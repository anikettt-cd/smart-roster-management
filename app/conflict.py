from collections import defaultdict
from datetime import date

def detect_conflicts(db, roster_id):
    from app.models import (Roster, RosterEntry, Employee, Brand, Process,
                            BrandProcessRequirement, Leave)
    roster = db.query(Roster).get(roster_id)
    entries = db.query(RosterEntry).filter(RosterEntry.roster_id == roster_id).all()
    # index
    by_emp_date = {}
    for e in entries:
        by_emp_date[(e.employee_id, e.date)] = e
    conflicts = []
    # 1. coverage gaps: for each req operating day, count working assigned
    reqs = db.query(BrandProcessRequirement).all()
    from app.models import PublicHoliday
    holiday_set = {h.date for h in db.query(PublicHoliday).all()}
    year, month = roster.year, roster.month
    import calendar
    ndays = calendar.monthrange(year, month)[1]
    dates = [date(year, month, d) for d in range(1, ndays+1)]
    # map entries by (brand,process,date)
    cov = defaultdict(lambda: defaultdict(int))  # (brand,process) -> date -> count
    # employee assignments
    from app.models import Assignment
    emp_assigns = defaultdict(set)
    for a in db.query(Assignment).all():
        emp_assigns[a.employee_id].add((a.brand_id, a.process_id))
    for e in entries:
        if e.status == "working" and e.brand_id:
            for (b, p) in emp_assigns[e.employee_id]:
                if b == e.brand_id:
                    cov[(b, p)][e.date] += 1
    for r in reqs:
        for d in dates:
            if not is_op_day(r.operating_calendar, d, holiday_set):
                continue
            ms = r.min_staff_per_day
            if r.min_staff_weekend and d.weekday() >= 5:
                ms = r.min_staff_weekend
            actual = cov[(r.brand_id, r.process_id)].get(d, 0)
            if actual < ms:
                brand = db.query(Brand).get(r.brand_id)
                proc = db.query(Process).get(r.process_id)
                conflicts.append({
                    "type": "coverage_gap",
                    "severity": "high",
                    "date": d.isoformat(),
                    "brand": brand.name if brand else r.brand_id,
                    "process": proc.name if proc else r.process_id,
                    "required": ms,
                    "actual": actual,
                    "message": f"{brand.name if brand else ''}/{proc.name if proc else ''} on {d}: required {ms}, have {actual}",
                })
    # 2. preferred off overridden
    for e in entries:
        if e.is_preferred_off_overridden:
            emp = db.query(Employee).get(e.employee_id)
            conflicts.append({
                "type": "preferred_off_overridden",
                "severity": "medium",
                "date": e.date.isoformat(),
                "employee": emp.name if emp else e.employee_id,
                "message": f"{emp.name if emp else ''} worked on preferred off {e.date}",
            })
    # 3. leave conflicts: employee marked working on a leave day (shouldn't happen) - check RosterEntry vs Leave
    leaves = db.query(Leave).filter(Leave.status == "approved").all()
    leave_set = {(lv.employee_id, lv.date) for lv in leaves}
    for e in entries:
        if e.status == "working" and (e.employee_id, e.date) in leave_set:
            emp = db.query(Employee).get(e.employee_id)
            conflicts.append({
                "type": "leave_conflict",
                "severity": "high",
                "date": e.date.isoformat(),
                "employee": emp.name if emp else e.employee_id,
                "message": f"{emp.name if emp else ''} scheduled to work on approved leave {e.date}",
            })
    # 4. double booking: employee working two brands same day (entries unique per emp/date so none) - skip
    return conflicts
def is_op_day(cal, d, holiday_set):
    if cal == "365":
        return True
    if cal == "daily_no_holidays":
        return d not in holiday_set
    if cal == "sun_holidays_off":
        return d.weekday() != 6 and d not in holiday_set
    return True
