# Smart Roster Management System

A browser-based roster management tool for planning, generating, validating, and managing monthly rosters across multiple brands, processes, pods, and employees.

## Features

- Manage employees, pods, brands, processes, assignments, working-day rules, public holidays, leaves.
- Configure brand/process operating calendars: 365-day, daily with holidays off, Sundays+holidays off.
- Minimum staffing requirements per brand/process.
- Generate a monthly roster with conflict detection and coverage gaps.
- Views: company, pod, brand, process, employee.
- Manual edits with validation.
- Handles changes: mark employee unavailable -> regenerates roster and flags gaps + backup suggestions.

## Tech Stack

- Backend: FastAPI (Python), SQLAlchemy, SQLite (configurable via DATABASE_URL).
- Frontend: Jinja2 templates + Tailwind CSS (CDN) + HTMX.
- Scheduling: deterministic greedy constraint solver.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn main:app --reload --port 8000
```

Open http://127.0.0.1:8000

## Docker

```bash
docker build -t smart-roster .
docker run -p 8000:8000 smart-roster
```

## Deployment

Deployable to Render/Railway/Fly.io using the Dockerfile. Set DATABASE_URL for Postgres if needed.

## Approach Note

### 1. How did you model employees, brands, processes, pods, and relationships?
Employees belong to a Pod (managed by a pod lead). Brands belong to a Pod. Processes are global. Assignments link Employee-Brand-Process (many-to-many). BrandProcessRequirement defines per brand+process operating calendar and min staff. Leaves and PublicHolidays are separate. Roster/RosterEntry store generated schedules.

### 2. How does the system generate a roster and determine constraints?
For each day, for each brand with operating processes, fill min staffing per process from assigned employees who are available (not on leave, not working another brand that day), preferring non-preferred-off days. One employee can cover multiple processes of the same brand. Coverage gaps are detected post-generation by comparing required vs actual per brand+process+day.

### 3. Single-resource vs multi-employee brands
Single-resource: one employee assigned to all processes of the brand; can cover all operating processes of that brand in a day. Multi-employee: employees specialized by process, with some overlap; scheduler assigns per process.

### 4. Unavailable employee managing all processes
System adds leave, regenerates roster, flags coverage gaps for that brand's processes on affected days, and suggests backup candidates assigned to same brand+process.

### 5. Conflicting requirements / insufficient staffing
Mandatory constraints (coverage, leaves) take priority over preferences (weekly offs). Conflicts are flagged with severity rather than silently generating invalid rosters.

### 6. Automated vs human control
Automated: roster generation, conflict detection, backup suggestions, regeneration. Human: approvals, manual edits, final publish, resolving flagged gaps.

### 7. Scaling
Move to Postgres, add caching, background jobs for generation, horizontal scaling of stateless API, optimize solver with CP-SAT for larger instances.

### 8. With one more week
CP-SAT solver (OR-Tools), preference-based optimization, approval workflows, CSV/Excel export, richer conflict explanations, tests.

## Assumptions

- Weekly offs are preferences; coverage takes priority.
- An employee can cover multiple processes of the same brand in one day but only one brand per day.
- Public holidays apply globally.
- Sample data uses 2026 holidays.
