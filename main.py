import os, sys
from datetime import date, datetime
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import init_db, SessionLocal, get_db
from app.models import *
from app.scheduler import generate_roster
from app.conflict import detect_conflicts

app = FastAPI(title="Smart Roster Management System")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.on_event("startup")
def startup():
    init_db()

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    rosters = db.query(Roster).order_by(Roster.year.desc(), Roster.month.desc()).all()
    counts = {
        "employees": db.query(Employee).count(),
        "brands": db.query(Brand).count(),
        "processes": db.query(Process).count(),
        "pods": db.query(Pod).count(),
    }
    return templates.TemplateResponse(request, "dashboard.html", {"request": request, "rosters": rosters, "counts": counts})

@app.get("/employees", response_class=HTMLResponse)
def employees_page(request: Request, db: Session = Depends(get_db)):
    emps = db.query(Employee).all()
    pods = db.query(Pod).all()
    return templates.TemplateResponse(request, "employees.html", {"request": request, "employees": emps, "pods": pods})

@app.post("/employees/add")
def add_employee(name: str = Form(...), pod_id: int = Form(None), role: str = Form("employee"), weekly_offs: str = Form("6"), db: Session = Depends(get_db)):
    offs = [int(x) for x in weekly_offs.split(",") if x.strip() != ""]
    e = Employee(name=name, pod_id=pod_id, role=role, weekly_offs=offs)
    db.add(e); db.commit()
    return RedirectResponse("/employees", status_code=303)

@app.get("/pods", response_class=HTMLResponse)
def pods_page(request: Request, db: Session = Depends(get_db)):
    pods = db.query(Pod).all()
    emps = db.query(Employee).all()
    return templates.TemplateResponse(request, "pods.html", {"request": request, "pods": pods, "employees": emps})

@app.get("/brands", response_class=HTMLResponse)
def brands_page(request: Request, db: Session = Depends(get_db)):
    brands = db.query(Brand).all()
    pods = db.query(Pod).all()
    processes = db.query(Process).all()
    return templates.TemplateResponse(request, "brands.html", {"request": request, "brands": brands, "pods": pods, "processes": processes})

@app.get("/processes", response_class=HTMLResponse)
def processes_page(request: Request, db: Session = Depends(get_db)):
    processes = db.query(Process).all()
    return templates.TemplateResponse(request, "processes.html", {"request": request, "processes": processes})

@app.post("/processes/add")
def add_process(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    db.add(Process(name=name, description=description)); db.commit()
    return RedirectResponse("/processes", status_code=303)

@app.get("/requirements", response_class=HTMLResponse)
def requirements_page(request: Request, db: Session = Depends(get_db)):
    reqs = db.query(BrandProcessRequirement).all()
    brands = db.query(Brand).all()
    processes = db.query(Process).all()
    return templates.TemplateResponse(request, "requirements.html", {"request": request, "reqs": reqs, "brands": brands, "processes": processes})

@app.post("/requirements/add")
def add_requirement(brand_id: int = Form(...), process_id: int = Form(...), operating_calendar: str = Form("daily_no_holidays"), min_staff_per_day: int = Form(1), db: Session = Depends(get_db)):
    r = BrandProcessRequirement(brand_id=brand_id, process_id=process_id, operating_calendar=operating_calendar, min_staff_per_day=min_staff_per_day)
    db.add(r); db.commit()
    return RedirectResponse("/requirements", status_code=303)

@app.get("/holidays", response_class=HTMLResponse)
def holidays_page(request: Request, db: Session = Depends(get_db)):
    holidays = db.query(PublicHoliday).order_by(PublicHoliday.date).all()
    return templates.TemplateResponse(request, "holidays.html", {"request": request, "holidays": holidays})

@app.post("/holidays/add")
def add_holiday(d: str = Form(...), name: str = Form(...), db: Session = Depends(get_db)):
    db.add(PublicHoliday(date=date.fromisoformat(d), name=name)); db.commit()
    return RedirectResponse("/holidays", status_code=303)

@app.get("/leaves", response_class=HTMLResponse)
def leaves_page(request: Request, db: Session = Depends(get_db)):
    leaves = db.query(Leave).all()
    employees = db.query(Employee).all()
    return templates.TemplateResponse(request, "leaves.html", {"request": request, "leaves": leaves, "employees": employees})

@app.post("/leaves/add")
def add_leave(employee_id: int = Form(...), d: str = Form(...), leave_type: str = Form("leave"), reason: str = Form(""), db: Session = Depends(get_db)):
    db.add(Leave(employee_id=employee_id, date=date.fromisoformat(d), leave_type=leave_type, status="approved", reason=reason)); db.commit()
    return RedirectResponse("/leaves", status_code=303)

@app.get("/assignments", response_class=HTMLResponse)
def assignments_page(request: Request, db: Session = Depends(get_db)):
    assigns = db.query(Assignment).all()
    employees = db.query(Employee).all()
    brands = db.query(Brand).all()
    processes = db.query(Process).all()
    return templates.TemplateResponse(request, "assignments.html", {"request": request, "assigns": assigns, "employees": employees, "brands": brands, "processes": processes})

@app.post("/assignments/add")
def add_assignment(employee_id: int = Form(...), brand_id: int = Form(...), process_id: int = Form(...), db: Session = Depends(get_db)):
    a = Assignment(employee_id=employee_id, brand_id=brand_id, process_id=process_id)
    db.add(a); db.commit()
    return RedirectResponse("/assignments", status_code=303)

@app.post("/roster/generate")
def generate(year: int = Form(...), month: int = Form(...), db: Session = Depends(get_db)):
    rid = generate_roster(db, year, month)
    return RedirectResponse(f"/roster/{rid}", status_code=303)

@app.get("/roster/{rid}", response_class=HTMLResponse)
def view_roster(request: Request, rid: int, view: str = "company", pod_id: int = None, brand_id: int = None, process_id: int = None, employee_id: int = None, db: Session = Depends(get_db)):
    roster = db.query(Roster).get(rid)
    if not roster:
        return RedirectResponse("/")
    import calendar
    year, month = roster.year, roster.month
    ndays = calendar.monthrange(year, month)[1]
    dates = [date(year, month, d) for d in range(1, ndays+1)]
    entries = db.query(RosterEntry).filter(RosterEntry.roster_id == rid).all()
    entry_map = {(e.employee_id, e.date): e for e in entries}
    # filter employees
    q = db.query(Employee)
    if pod_id:
        q = q.filter(Employee.pod_id == pod_id)
    employees = q.all()
    # brand filter: employees assigned to brand
    if brand_id:
        assigns = db.query(Assignment).filter(Assignment.brand_id == brand_id).all()
        eids = {a.employee_id for a in assigns}
        employees = [e for e in employees if e.id in eids]
    if process_id:
        assigns = db.query(Assignment).filter(Assignment.process_id == process_id).all()
        eids = {a.employee_id for a in assigns}
        employees = [e for e in employees if e.id in eids]
    if employee_id:
        employees = [e for e in employees if e.id == employee_id]
    # brands/processes/pods for filters
    brands = db.query(Brand).all()
    processes = db.query(Process).all()
    pods = db.query(Pod).all()
    all_employees = db.query(Employee).all()
    # coverage summary for brand view
    cov_summary = None
    if brand_id:
        # daily counts per process
        cov_summary = {}
        reqs = db.query(BrandProcessRequirement).filter(BrandProcessRequirement.brand_id == brand_id).all()
        for r in reqs:
            proc = db.query(Process).get(r.process_id)
            counts = {}
            for d in dates:
                c = 0
                for e in entries:
                    if e.brand_id == brand_id and e.date == d and e.status == "working":
                        assigns = db.query(Assignment).filter(Assignment.employee_id == e.employee_id, Assignment.brand_id == brand_id, Assignment.process_id == r.process_id).first()
                        if assigns:
                            c += 1
                counts[d] = c
            cov_summary[proc.name] = (r, counts)
    return templates.TemplateResponse(request, "roster.html", {
        "request": request, "roster": roster, "dates": dates, "employees": employees,
        "entry_map": entry_map, "view": view, "pods": pods, "brands": brands,
        "processes": processes, "all_employees": all_employees, "pod_id": pod_id,
        "brand_id": brand_id, "process_id": process_id, "employee_id": employee_id,
        "cov_summary": cov_summary,
    })

@app.get("/roster/{rid}/conflicts", response_class=HTMLResponse)
def conflicts_page(request: Request, rid: int, db: Session = Depends(get_db)):
    roster = db.query(Roster).get(rid)
    conflicts = detect_conflicts(db, rid)
    return templates.TemplateResponse(request, "conflicts.html", {"request": request, "roster": roster, "conflicts": conflicts})

@app.post("/roster/{rid}/entry/update")
def update_entry(rid: int, employee_id: int = Form(...), d: str = Form(...), status: str = Form(...), brand_id: int = Form(None), process_id: int = Form(None), db: Session = Depends(get_db)):
    dt = date.fromisoformat(d)
    e = db.query(RosterEntry).filter(RosterEntry.roster_id == rid, RosterEntry.employee_id == employee_id, RosterEntry.date == dt).first()
    if e:
        e.status = status
        e.brand_id = brand_id if brand_id else None
        e.process_id = process_id if process_id else None
    else:
        e = RosterEntry(roster_id=rid, employee_id=employee_id, date=dt, status=status, brand_id=brand_id or None, process_id=process_id or None)
        db.add(e)
    db.commit()
    return RedirectResponse(f"/roster/{rid}", status_code=303)

@app.post("/roster/{rid}/publish")
def publish(rid: int, db: Session = Depends(get_db)):
    r = db.query(Roster).get(rid)
    r.status = "published"
    db.commit()
    return RedirectResponse(f"/roster/{rid}", status_code=303)

@app.post("/change/unavailable")
def mark_unavailable(employee_id: int = Form(...), d: str = Form(...), db: Session = Depends(get_db)):
    dt = date.fromisoformat(d)
    db.add(Leave(employee_id=employee_id, date=dt, leave_type="unavailable", status="approved", reason="Ad-hoc unavailability"))
    db.commit()
    # regenerate affected roster if exists
    r = db.query(Roster).filter(Roster.year == dt.year, Roster.month == dt.month).first()
    if r:
        generate_roster(db, dt.year, dt.month, roster_id=r.id)
        return RedirectResponse(f"/roster/{r.id}/conflicts", status_code=303)
    return RedirectResponse("/leaves", status_code=303)

@app.get("/backup/{rid}/{employee_id}/{d}")
def backup_suggestions(request: Request, rid: int, employee_id: int, d: str, db: Session = Depends(get_db)):
    dt = date.fromisoformat(d)
    entry = db.query(RosterEntry).filter(RosterEntry.roster_id == rid, RosterEntry.employee_id == employee_id, RosterEntry.date == dt).first()
    brand_id = entry.brand_id if entry else None
    process_id = entry.process_id if entry else None
    # candidates: assigned to same brand+process, not on leave that day
    cands = []
    if brand_id and process_id:
        assigns = db.query(Assignment).filter(Assignment.brand_id == brand_id, Assignment.process_id == process_id).all()
        for a in assigns:
            if a.employee_id == employee_id:
                continue
            # check availability: no leave
            lv = db.query(Leave).filter(Leave.employee_id == a.employee_id, Leave.date == dt, Leave.status == "approved").first()
            if lv:
                continue
            emp = db.query(Employee).get(a.employee_id)
            cands.append(emp)
    return templates.TemplateResponse(request, "backup.html", {"request": request, "candidates": cands, "employee_id": employee_id, "d": d, "rid": rid})

