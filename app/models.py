from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Pod(Base):
    __tablename__ = "pods"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    lead_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    description = Column(Text)
    employees = relationship("Employee", back_populates="pod", foreign_keys="Employee.pod_id")

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120))
    pod_id = Column(Integer, ForeignKey("pods.id"), nullable=True)
    role = Column(String(50), default="employee")
    weekly_offs = Column(JSON, default=list)
    max_work_days_per_week = Column(Integer, default=6)
    preferences = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    pod = relationship("Pod", back_populates="employees", foreign_keys=[pod_id])
class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    pod_id = Column(Integer, ForeignKey("pods.id"), nullable=True)
    description = Column(Text)
    assignments = relationship("Assignment", back_populates="brand")
    requirements = relationship("BrandProcessRequirement", back_populates="brand")

class Process(Base):
    __tablename__ = "processes"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=False)
    __table_args__ = (UniqueConstraint("employee_id", "brand_id", "process_id", name="uq_assignment"),)
    employee = relationship("Employee")
    brand = relationship("Brand", back_populates="assignments")
    process = relationship("Process")

class BrandProcessRequirement(Base):
    __tablename__ = "brand_process_requirements"
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=False)
    operating_calendar = Column(String(30), default="daily_no_holidays")
    min_staff_per_day = Column(Integer, default=1)
    min_staff_weekend = Column(Integer, nullable=True)
    notes = Column(Text)
    brand = relationship("Brand", back_populates="requirements")
    process = relationship("Process")

class PublicHoliday(Base):
    __tablename__ = "public_holidays"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True)
    name = Column(String(100), nullable=False)

class Leave(Base):
    __tablename__ = "leaves"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    leave_type = Column(String(30), default="leave")
    status = Column(String(20), default="approved")
    reason = Column(Text)
    employee = relationship("Employee")

class Roster(Base):
    __tablename__ = "rosters"
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    status = Column(String(20), default="draft")
    generated_at = Column(String(40))
    notes = Column(Text)
    entries = relationship("RosterEntry", back_populates="roster", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("year", "month", name="uq_roster_month"),)

class RosterEntry(Base):
    __tablename__ = "roster_entries"
    id = Column(Integer, primary_key=True)
    roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(20), default="off")
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    is_preferred_off_overridden = Column(Boolean, default=False)
    notes = Column(Text)
    roster = relationship("Roster", back_populates="entries")
    employee = relationship("Employee")
    brand = relationship("Brand")
    process = relationship("Process")
    __table_args__ = (UniqueConstraint("roster_id", "employee_id", "date", name="uq_entry"),)

