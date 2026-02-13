# TaskTimer - Quick Start Guides

## FORGE Quick Start (5 min)

```bash
# Monitor team productivity
tasktimer report weekly
tasktimer list --limit 100 --category development
```

## ATLAS Quick Start (5 min)

```bash
# Track build sessions
tasktimer start "Building ToolX" --category development --duration 90
tasktimer stop --notes "Completed Phase 4"
```

## CLIO Quick Start (5 min)

```bash
# Linux CLI usage
tasktimer start "System maintenance"
tasktimer status
tasktimer stop
```

## NEXUS Quick Start (5 min)

```python
# Cross-platform Python usage
from tasktimer import TaskTimer
timer = TaskTimer()
timer.start_session("Task", duration=1500)
```

## BOLT Quick Start (5 min)

```bash
# Free executor - no API costs
tasktimer start "Batch processing"
# ... work ...
tasktimer stop
```

**Built by:** ATLAS (Team Brain)
**Date:** February 12, 2026
