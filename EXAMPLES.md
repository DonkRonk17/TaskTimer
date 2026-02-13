# TaskTimer - Usage Examples

Complete collection of TaskTimer usage examples from basic to advanced workflows.

---

## Example 1: Your First Pomodoro

**Scenario:** First time using TaskTimer

**Steps:**
```bash
# Start 25-minute work session
tasktimer start "Learn TaskTimer basics"

# Check current status
tasktimer status
# Output: Active session, elapsed time, remaining time

# Complete session
tasktimer stop --notes "Learned basic commands"
```

**What You Learned:** Start, check status, stop with notes

---

## Example 2: Custom Duration Session

**Scenario:** Need longer focus session than default 25 minutes

**Steps:**
```bash
# 90-minute deep work
tasktimer start "Implement authentication" --duration 90 --category development

# Work...

# Stop when done
tasktimer stop
```

---

## Example 3: Handling Interruptions

**Scenario:** Phone call during work session

**Steps:**
```bash
# Start work
tasktimer start "Code review"

# Interruption! Pause timer
tasktimer pause

# After interruption, resume
tasktimer resume

# Finish work
tasktimer stop
```

---

## Example 4: Daily Productivity Review

**Scenario:** End of day, want to see what you accomplished

**Steps:**
```bash
# List today's sessions
tasktimer list --limit 20

# Get detailed daily report
tasktimer report daily

# Example output:
# Total Sessions: 8
# Focus Hours: 5.2h
# Focus Score: 78/100
```

---

## Example 5: Weekly Retrospective

**Scenario:** Sunday planning, review last week's productivity

**Steps:**
```bash
# Get weekly summary
tasktimer report weekly

# Compare trends
tasktimer report weekly --date 2026-02-03  # Previous week
```

---

## Example 6: Category-Based Analysis

**Scenario:** Track different types of work

**Steps:**
```bash
# Track by category
tasktimer start "Sprint planning" --category meetings --duration 60
tasktimer start "Bug fix #42" --category development --duration 45
tasktimer start "Unit tests" --category testing --duration 30

# Later, filter by category
tasktimer list --category development
tasktimer list --category meetings
```

---

## Example 7: Integration with AgentHeartbeat

**Scenario:** Correlate timer with agent activity

**Code:**
```python
from agentheartbeat import AgentHeartbeatMonitor
from tasktimer import TaskTimer

heartbeat = AgentHeartbeatMonitor()
timer = TaskTimer()

# Start heartbeat
hb_id = heartbeat.emit_heartbeat(
    agent_id="ATLAS",
    status="working",
    task="Building feature"
)

# Link timer to heartbeat
session_id = timer.start_session(
    task_name="Build authentication feature",
    duration=90,
    heartbeat_id=hb_id
)

# Work...

timer.stop_session()
```

---

## Example 8: Integration with TaskQueuePro

**Scenario:** Time a specific queue task

**Code:**
```python
from taskqueuepro import TaskQueuePro
from tasktimer import TaskTimer

queue = TaskQueuePro()
timer = TaskTimer()

# Get task from queue
task = queue.get_next_task("ATLAS")

# Start timer for task
session_id = timer.start_session(
    task_name=task.title,
    task_queue_id=task.task_id
)

# Complete both
timer.stop_session(notes="Completed successfully")
queue.complete_task(task.task_id)
```

---

## Example 9: Export Data for Analysis

**Scenario:** Want to analyze productivity data in Excel

**Code:**
```python
from tasktimer import TaskTimer
from dataconvert import DataConvert

timer = TaskTimer()
converter = DataConvert()

# Get sessions
sessions = timer.sessions.list_sessions(
    start_date="2026-02-01",
    end_date="2026-02-15",
    limit=1000
)

# Export to CSV
csv_data = converter.to_csv(sessions)
with open('productivity_data.csv', 'w') as f:
    f.write(csv_data)
```

---

## Example 10: Automated Notifications

**Scenario:** Notify team when important sessions complete

**Code:**
```python
from synapselink import quick_send
from tasktimer import TaskTimer

timer = TaskTimer()

# Critical work session
session_id = timer.start_session(
    task_name="Production deployment",
    duration=120,
    category="operations"
)

# Work...

session = timer.stop_session()

# Notify team
if session['duration_seconds'] > 3600:  # >1 hour
    quick_send(
        "FORGE,LOGAN",
        "Long Session Complete",
        f"Finished: {session['task_name']} ({session['duration_seconds']//60} min)",
        priority="HIGH"
    )
```

---

## Example 11: Multi-Session Day Tracking

**Scenario:** Track full workday with multiple focus blocks

**Steps:**
```bash
# Morning
tasktimer start "Email and planning" --duration 30 --category admin
tasktimer stop

tasktimer start "Feature development" --duration 90 --category development
tasktimer stop

# Lunch break (no timer)

# Afternoon
tasktimer start "Code review" --duration 60 --category development
tasktimer stop

tasktimer start "Documentation" --duration 45 --category documentation
tasktimer stop

# End of day review
tasktimer report daily
```

---

## Example 12: Testing Mode (Short Durations)

**Scenario:** Testing TaskTimer functionality

**Steps:**
```bash
# 1-minute test session
tasktimer start "Test session" --duration 1

# Wait 60 seconds

# Check it completed
tasktimer status
tasktimer stop
```

---

For more examples, see README.md and INTEGRATION_EXAMPLES.md

**Last Updated:** February 12, 2026  
**Maintained By:** ATLAS (Team Brain)
