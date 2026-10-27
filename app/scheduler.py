import calendar
from datetime import date, timedelta
from collections import defaultdict, Counter

def is_operating_day(cal, d, holiday_set):
    if cal == "365":
        return True
    if cal == "daily_no_holidays":
        return d not in holiday_set
    if cal == "sun_holidays_off":
        return d.weekday() != 6 and d not in holiday_set
    return True

def month_dates(year, month):
    ndays = calendar.monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, ndays+1)]
def generate_roster(db, year, month, roster_id=None):
    from app.models import (Employee, Brand, Process, Assignment, BrandProcessRequirement,
                            PublicHoliday, Leave, Roster, RosterEntry)
    from datetime import datetime
    holidays = {h.date for h in db.query(PublicHoliday).all()}
    dates = month_dates(year, month)
    employees = db.query(Employee).filter(Employee.active == True).all()
    emp_by_id = {e.id: e for e in employees}
    assignments = db.query(Assignment).all()
    bp_emps = defaultdict(list)
    emp_brands = defaultdict(set)
    emp_processes = defaultdict(set)
    for a in assignments:
        bp_emps[(a.brand_id, a.process_id)].append(a.employee_id)
        emp_brands[a.employee_id].add(a.brand_id)
        emp_processes[a.employee_id].add((a.brand_id, a.process_id))
    reqs = db.query(BrandProcessRequirement).all()
    reqs_by_brand = defaultdict(list)
    for r in reqs:
        reqs_by_brand[r.brand_id].append(r)
    leaves = db.query(Leave).filter(Leave.status == "approved").all()
    leave_map = defaultdict(set)
    for lv in leaves:
        leave_map[lv.employee_id].add(lv.date)
    work_count = Counter()
    entries = []
    entry_index = {}
    def add_entry(emp_id, d, status, brand_id=None, process_id=None, overridden=False):
        e = {"employee_id": emp_id, "date": d, "status": status,
             "brand_id": brand_id, "process_id": process_id,
             "is_preferred_off_overridden": overridden}
        entries.append(e)
        entry_index[(emp_id, d)] = e
    for emp in employees:
        for d in dates:
            if d in leave_map[emp.id]:
                add_entry(emp.id, d, "leave")

    for d in dates:
        brands_today = []
        for bid, rs in reqs_by_brand.items():
            ops = [r for r in rs if is_operating_day(r.operating_calendar, d, holidays)]
            if ops:
                brands_today.append((bid, ops))
        brands_today.sort(key=lambda x: -sum((r.min_staff_weekend if (r.min_staff_weekend and d.weekday()>=5) else r.min_staff_per_day) for r in x[1]))
        emp_brand_today = {}
        counted_today = set()
        process_filled = defaultdict(int)
        process_used_emps = defaultdict(set)
        for (bid, ops) in brands_today:
            ops_sorted = sorted(ops, key=lambda r: -((r.min_staff_weekend if (r.min_staff_weekend and d.weekday()>=5) else r.min_staff_per_day)))
            for r in ops_sorted:
                ms = r.min_staff_per_day
                if r.min_staff_weekend and d.weekday() >= 5:
                    ms = r.min_staff_weekend
                cands = []
                for eid in bp_emps[(bid, r.process_id)]:
                    if (eid, d) in entry_index and entry_index[(eid,d)]["status"] == "leave":
                        continue
                    emp = emp_by_id.get(eid)
                    if not emp or not emp.active:
                        continue
                    if eid in emp_brand_today and emp_brand_today[eid] != bid:
                        continue
                    if eid in process_used_emps[(bid, r.process_id)]:
                        continue
                    preferred_off = d.weekday() in (emp.weekly_offs or [])
                    cands.append((eid, preferred_off))
                cands.sort(key=lambda x: (x[1], work_count[x[0]]))
                filled = process_filled[(bid, r.process_id)]
                for (eid, pref) in cands:
                    if filled >= ms:
                        break
                    if eid in process_used_emps[(bid, r.process_id)]:
                        continue
                    process_used_emps[(bid, r.process_id)].add(eid)
                    process_filled[(bid, r.process_id)] += 1
                    filled += 1
                    overridden = pref
                    if eid not in emp_brand_today:
                        emp_brand_today[eid] = bid
                        add_entry(eid, d, "working", brand_id=bid, process_id=None, overridden=overridden)
                        if eid not in counted_today:
                            work_count[eid] += 1
                            counted_today.add(eid)
        for emp in employees:
            if (emp.id, d) in entry_index:
                continue
            if d in holidays:
                add_entry(emp.id, d, "holiday")
            else:
                add_entry(emp.id, d, "off")

    if roster_id is None:
        existing = db.query(Roster).filter(Roster.year == year, Roster.month == month).first()
        if existing:
            db.query(RosterEntry).filter(RosterEntry.roster_id == existing.id).delete()
            roster = existing
        else:
            roster = Roster(year=year, month=month, status="draft", generated_at=datetime.utcnow().isoformat())
            db.add(roster)
            db.flush()
    else:
        roster = db.query(Roster).get(roster_id)
        db.query(RosterEntry).filter(RosterEntry.roster_id == roster.id).delete()
    for e in entries:
        re = RosterEntry(
            roster_id=roster.id,
            employee_id=e["employee_id"],
            date=e["date"],
            status=e["status"],
            brand_id=e["brand_id"],
            process_id=e["process_id"],
            is_preferred_off_overridden=e["is_preferred_off_overridden"],
        )
        db.add(re)
    db.commit()
    return roster.id

