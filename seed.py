import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import init_db, SessionLocal
from app.models import (Pod, Employee, Brand, Process, Assignment,
                        BrandProcessRequirement, PublicHoliday, Leave)
from datetime import date, timedelta
def seed():
    db = SessionLocal()
    for t in [Leave, Assignment, BrandProcessRequirement, Brand, Process, Employee, Pod, PublicHoliday]:
        db.query(t).delete()
    db.commit()
    proc_names = ["Customer Support", "Abandoned Cart", "Retention", "NDR Management", "Order Tracking"]
    procs = {}
    for n in proc_names:
        p = Process(name=n, description=n)
        db.add(p); db.flush()
        procs[n] = p.id
    pods = {}
    for name in ["Pod Alpha", "Pod Beta", "Pod Gamma", "Pod Delta"]:
        pod = Pod(name=name, description=name)
        db.add(pod); db.flush()
        pods[name] = pod.id
    emp_id = {}
    def add_emp(name, pod, role="employee", weekly_offs=None):
        e = Employee(name=name, email=name.lower().replace(" ",".")+"@company.com",
                     pod_id=pods[pod], role=role, weekly_offs=weekly_offs or [6],
                     max_work_days_per_week=6)
        db.add(e); db.flush()
        emp_id[name] = e.id
        return e.id
    leads = {"Pod Alpha":"Aarav Lead","Pod Beta":"Diya Lead","Pod Gamma":"Kabir Lead","Pod Delta":"Meera Lead"}
    for pod, leadname in leads.items():
        add_emp(leadname, pod, role="pod_lead", weekly_offs=[6])
    worker_names = ["Riya Sharma","Vikram Singh","Ananya Gupta","Rohan Mehta","Priya Nair","Arjun Reddy","Sneha Iyer","Karan Malhotra","Neha Kapoor","Aditya Joshi","Pooja Verma","Siddharth Rao","Kavya Menon","Manish Tiwari","Divya Pillai","Harsh Agarwal","Tanvi Desai","Nikhil Bhat","Isha Choudhary","Yash Patel","Ritu Saxena","Gaurav Kumar","Shweta Mishra","Abhishek Jain","Nisha Roy","Prateek Das","Bhavna Kulkarni","Saurabh Sinha"]
    pod_list = ["Pod Alpha","Pod Beta","Pod Gamma","Pod Delta"]
    for i, w in enumerate(worker_names):
        add_emp(w, pod_list[i % 4], weekly_offs=[i % 7] if i%3==0 else [6])

    brand_specs = [
        ("Brand Nova", "Pod Alpha", [("Customer Support","365",1),("Abandoned Cart","sun_holidays_off",1)]),
        ("Brand Orion", "Pod Alpha", [("Customer Support","daily_no_holidays",1),("NDR Management","daily_no_holidays",1)]),
        ("Brand Pixel", "Pod Alpha", [("Customer Support","365",1)]),
        ("Brand Quest", "Pod Alpha", [("Customer Support","sun_holidays_off",1),("Retention","sun_holidays_off",1)]),
        ("Brand Rhea", "Pod Beta", [("Customer Support","365",2)]),
        ("Brand Solis", "Pod Beta", [("Customer Support","daily_no_holidays",1),("Abandoned Cart","daily_no_holidays",1),("Retention","daily_no_holidays",1)]),
        ("Brand Taro", "Pod Beta", [("Customer Support","365",1)]),
        ("Brand Ursa", "Pod Beta", [("NDR Management","sun_holidays_off",1)]),
        ("Brand Vela", "Pod Gamma", [("Customer Support","365",1),("Order Tracking","365",1)]),
        ("Brand Wisp", "Pod Gamma", [("Customer Support","daily_no_holidays",1)]),
        ("Brand Xeno", "Pod Gamma", [("Customer Support","365",1),("Abandoned Cart","365",1)]),
        ("Brand Yara", "Pod Delta", [("Customer Support","365",1)]),
        ("Brand Zeta", "Pod Delta", [("Customer Support","sun_holidays_off",1),("Retention","sun_holidays_off",1)]),
    ]
    brands = {}
    for (bname, pod, reqs) in brand_specs:
        br = Brand(name=bname, pod_id=pods[pod], description=bname)
        db.add(br); db.flush()
        brands[bname] = br.id
        for (pname, cal, ms) in reqs:
            r = BrandProcessRequirement(brand_id=br.id, process_id=procs[pname],
                                       operating_calendar=cal, min_staff_per_day=ms)
            db.add(r)
    db.commit()

    brand_list = list(brands.keys())
    single_brands = brand_list[:10]
    multi_brands = brand_list[10:]
    widx = 0
    workers = worker_names[:]
    for bname in single_brands:
        w = workers[widx % len(workers)]
        widx += 1
        bid = brands[bname]
        reqs = [r for r in db.query(BrandProcessRequirement).filter(BrandProcessRequirement.brand_id==bid).all()]
        for r in reqs:
            db.add(Assignment(employee_id=emp_id[w], brand_id=bid, process_id=r.process_id))
    db.commit()
    for bname in multi_brands:
        bid = brands[bname]
        reqs = db.query(BrandProcessRequirement).filter(BrandProcessRequirement.brand_id==bid).all()
        for i, r in enumerate(reqs):
            w = workers[(widx + i) % len(workers)]
            db.add(Assignment(employee_id=emp_id[w], brand_id=bid, process_id=r.process_id))
        if len(reqs) >= 1:
            w2 = workers[(widx + len(reqs)) % len(workers)]
            db.add(Assignment(employee_id=emp_id[w2], brand_id=bid, process_id=reqs[0].process_id))
        if len(reqs) >= 2:
            w3 = workers[(widx + len(reqs) + 1) % len(workers)]
            db.add(Assignment(employee_id=emp_id[w3], brand_id=bid, process_id=reqs[1].process_id))
        widx += 3
    db.commit()

    holiday_dates = [(date(2026,1,26),"Republic Day"),(date(2026,3,4),"Holi"),(date(2026,4,2),"Ram Navami"),(date(2026,5,1),"May Day"),(date(2026,8,15),"Independence Day"),(date(2026,10,2),"Gandhi Jayanti"),(date(2026,10,20),"Dussehra"),(date(2026,11,9),"Diwali"),(date(2026,12,25),"Christmas")]
    for d, n in holiday_dates:
        db.add(PublicHoliday(date=d, name=n))
    db.commit()
    import random
    random.seed(42)
    for w in worker_names[:8]:
        d = date(2026, 1, random.randint(5, 25))
        db.add(Leave(employee_id=emp_id[w], date=d, leave_type="leave", status="approved", reason="Personal"))
    db.add(Leave(employee_id=emp_id[worker_names[0]], date=date(2026,1,10), leave_type="comp_off", status="approved", reason="Comp off"))
    db.commit()
    db.close()
    print("Seeded.")

if __name__ == "__main__":
    init_db()
    seed()

