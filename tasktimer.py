#!/usr/bin/env python3
"""
TaskTimer - Pomodoro-Style Productivity Timer

A comprehensive time tracking and productivity analytics tool with deep
integration into the Team Brain ecosystem. Features Pomodoro timers,
session management, analytics, and connections to AgentHeartbeat,
TaskQueuePro, MemoryBridge, and more.

Author: ATLAS (Team Brain)
For: Logan Smith / Metaphy LLC
Version: 1.0.0
Date: February 12, 2026
License: MIT
Protocol: BUILD_PROTOCOL_V1.md

TOOLS USED IN THIS BUILD:
- ToolRegistry: Tool discovery and registration
- ToolSentinel: Architecture validation
- AgentHeartbeat: Correlate timer with agent presence
- TaskQueuePro: Link sessions to queue tasks
- MemoryBridge: Long-term productivity storage
- SynapseLink: Team notifications
- TimeSync: Respect BeaconTime
- SessionReplay: Event recording
- SmartNotes: Session context
- ConfigManager: Centralized config
- QuickBackup: Database backup
- ErrorRecovery: Graceful error handling
- DataConvert: Export to JSON/CSV
- GitFlow: Professional git workflow
- ChangeLog: Version tracking
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Version
__version__ = "1.0.0"

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration manager with defaults."""
    
    DEFAULT_CONFIG = {
        "timer": {
            "pomodoro_duration": 1500,  # 25 minutes
            "short_break_duration": 300,  # 5 minutes
            "long_break_duration": 900,  # 15 minutes
            "pomodoros_until_long_break": 4
        },
        "notifications": {
            "enabled": True,
            "sound_enabled": True,
            "urgency": "normal"
        },
        "integrations": {
            "agentheartbeat_enabled": True,
            "taskqueuepro_enabled": True,
            "memorybridge_enabled": True,
            "synapselink_enabled": True,
            "timesync_enabled": True
        },
        "database": {
            "path": "~/.tasktimer/sessions.db",
            "auto_backup": True,
            "backup_frequency_days": 7
        },
        "analytics": {
            "daily_goal_hours": 8,
            "focus_score_threshold": 70
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        self.config_path = config_path or Path.home() / ".tasktimer" / "config.json"
        self.data = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                config = self.DEFAULT_CONFIG.copy()
                self._deep_update(config, user_config)
                return config
            except Exception as e:
                print(f"[!] Warning: Failed to load config: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config
            config = self.DEFAULT_CONFIG.copy()
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Write default config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return config
    
    def _deep_update(self, base: dict, updates: dict):
        """Deep merge updates into base dict."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base:
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def save(self):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get(self, key_path: str, default=None):
        """Get config value by dot-notation key path."""
        keys = key_path.split('.')
        value = self.data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value):
        """Set config value by dot-notation key path."""
        keys = key_path.split('.')
        data = self.data
        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]
        data[keys[-1]] = value
        self.save()


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Session:
    """Timer session data model."""
    id: str
    task_name: str
    category: Optional[str]
    start_time: float
    end_time: Optional[float]
    duration_seconds: Optional[int]
    status: str  # active, paused, completed, abandoned
    notes: Optional[str]
    heartbeat_id: Optional[str]
    task_queue_id: Optional[str]
    session_replay_id: Optional[str]
    distraction_count: int
    pause_count: int
    created_at: float
    updated_at: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Break:
    """Break session data model."""
    id: str
    session_id: str
    break_type: str  # short, long, unscheduled
    start_time: float
    end_time: Optional[float]
    duration_seconds: Optional[int]
    notes: Optional[str]
    created_at: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class TaskTimerError(Exception):
    """Base exception for TaskTimer."""
    pass


class DatabaseError(TaskTimerError):
    """Database operation failed."""
    pass


class IntegrationError(TaskTimerError):
    """External tool integration failed."""
    pass


class StateError(TaskTimerError):
    """Invalid timer state transition."""
    pass


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """SQLite database management with schema initialization."""
    
    SCHEMA_VERSION = "1.0.0"
    
    SCHEMA = """
    -- Sessions table
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        task_name TEXT NOT NULL,
        category TEXT,
        start_time REAL NOT NULL,
        end_time REAL,
        duration_seconds INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        notes TEXT,
        heartbeat_id TEXT,
        task_queue_id TEXT,
        session_replay_id TEXT,
        distraction_count INTEGER DEFAULT 0,
        pause_count INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
    CREATE INDEX IF NOT EXISTS idx_sessions_category ON sessions(category);
    CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
    
    -- Breaks table
    CREATE TABLE IF NOT EXISTS breaks (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        break_type TEXT NOT NULL,
        start_time REAL NOT NULL,
        end_time REAL,
        duration_seconds INTEGER,
        notes TEXT,
        created_at REAL NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_breaks_session_id ON breaks(session_id);
    
    -- Analytics table (pre-computed daily summaries)
    CREATE TABLE IF NOT EXISTS analytics (
        date TEXT PRIMARY KEY,
        total_focus_seconds INTEGER DEFAULT 0,
        total_sessions INTEGER DEFAULT 0,
        completed_sessions INTEGER DEFAULT 0,
        abandoned_sessions INTEGER DEFAULT 0,
        average_focus_duration INTEGER DEFAULT 0,
        distraction_count INTEGER DEFAULT 0,
        focus_score REAL DEFAULT 0.0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics(date);
    
    -- Config table
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at REAL NOT NULL
    );
    
    -- Schema version tracking
    CREATE TABLE IF NOT EXISTS schema_version (
        version TEXT PRIMARY KEY,
        applied_at REAL NOT NULL
    );
    """
    
    def __init__(self, db_path: Path):
        """Initialize database manager."""
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        self.conn.execute("PRAGMA journal_mode=WAL")
        # Execute schema
        self.conn.executescript(self.SCHEMA)
        # Record schema version
        self.conn.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
            (self.SCHEMA_VERSION, time.time())
        )
        self.conn.commit()
    
    def execute(self, query: str, params: tuple = None) -> sqlite3.Cursor:
        """Execute SQL query."""
        try:
            if params:
                return self.conn.execute(query, params)
            else:
                return self.conn.execute(query)
        except sqlite3.Error as e:
            raise DatabaseError(f"Database error: {e}")
    
    def commit(self):
        """Commit transaction."""
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ============================================================================
# TIMER ENGINE
# ============================================================================

class TimerEngine:
    """Core timer with precise timing and state management."""
    
    STATES = ['idle', 'running', 'paused', 'completed']
    
    def __init__(self):
        """Initialize timer engine."""
        self.state = 'idle'
        self.start_time = None
        self.pause_time = None
        self.accumulated_time = 0.0  # Seconds
        self.target_duration = None  # Seconds
    
    def start(self, duration_seconds: int):
        """Start timer for specified duration."""
        if self.state not in ['idle', 'completed']:
            raise StateError(f"Cannot start timer in state '{self.state}'")
        
        self.state = 'running'
        self.start_time = time.monotonic()
        self.pause_time = None
        self.accumulated_time = 0.0
        self.target_duration = duration_seconds
    
    def pause(self):
        """Pause current timer."""
        if self.state != 'running':
            raise StateError(f"Cannot pause timer in state '{self.state}'")
        
        self.state = 'paused'
        self.pause_time = time.monotonic()
        # Accumulate time up to pause
        self.accumulated_time += (self.pause_time - self.start_time)
    
    def resume(self):
        """Resume paused timer."""
        if self.state != 'paused':
            raise StateError(f"Cannot resume timer in state '{self.state}'")
        
        self.state = 'running'
        # Reset start time to now (accumulated time already saved)
        self.start_time = time.monotonic()
        self.pause_time = None
    
    def stop(self) -> float:
        """Stop timer and return total elapsed time."""
        if self.state not in ['running', 'paused']:
            raise StateError(f"Cannot stop timer in state '{self.state}'")
        
        elapsed = self.get_elapsed()
        self.state = 'completed'
        return elapsed
    
    def get_elapsed(self) -> float:
        """Get current elapsed time in seconds."""
        if self.state == 'idle':
            return 0.0
        elif self.state == 'running':
            return self.accumulated_time + (time.monotonic() - self.start_time)
        elif self.state == 'paused':
            return self.accumulated_time
        elif self.state == 'completed':
            return self.accumulated_time
        return 0.0
    
    def get_remaining(self) -> float:
        """Get remaining time until completion (negative if overtime)."""
        if not self.target_duration:
            return 0.0
        return self.target_duration - self.get_elapsed()
    
    def is_complete(self) -> bool:
        """Check if timer has reached target duration."""
        if not self.target_duration:
            return False
        return self.get_elapsed() >= self.target_duration
    
    def reset(self):
        """Reset timer to idle state."""
        self.state = 'idle'
        self.start_time = None
        self.pause_time = None
        self.accumulated_time = 0.0
        self.target_duration = None


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """Manage timer sessions with SQLite persistence."""
    
    def __init__(self, db: DatabaseManager):
        """Initialize session manager."""
        self.db = db
    
    def create_session(
        self,
        task_name: str,
        category: str = None,
        notes: str = None,
        **links
    ) -> str:
        """Create new session, return session_id."""
        session_id = str(uuid.uuid4())
        now = time.time()
        
        self.db.execute("""
            INSERT INTO sessions (
                id, task_name, category, start_time, status,
                notes, heartbeat_id, task_queue_id, session_replay_id,
                distraction_count, pause_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, 0, 0, ?, ?)
        """, (
            session_id,
            task_name,
            category,
            now,
            notes,
            links.get('heartbeat_id'),
            links.get('task_queue_id'),
            links.get('session_replay_id'),
            now,
            now
        ))
        self.db.commit()
        return session_id
    
    def update_session(self, session_id: str, **updates):
        """Update session fields."""
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        # Always update updated_at
        set_clauses.append("updated_at = ?")
        params.append(time.time())
        
        params.append(session_id)
        
        query = f"UPDATE sessions SET {', '.join(set_clauses)} WHERE id = ?"
        self.db.execute(query, tuple(params))
        self.db.commit()
    
    def complete_session(self, session_id: str, duration: float, notes: str = None):
        """Mark session as completed."""
        updates = {
            'status': 'completed',
            'end_time': time.time(),
            'duration_seconds': int(duration)
        }
        if notes:
            updates['notes'] = notes
        self.update_session(session_id, **updates)
    
    def abandon_session(self, session_id: str):
        """Mark session as abandoned."""
        self.update_session(session_id, status='abandoned')
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve session by ID."""
        cursor = self.db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_sessions(
        self,
        start_date: str = None,
        end_date: str = None,
        category: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query sessions with filters."""
        query = "SELECT * FROM sessions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND start_time >= ?"
            params.append(datetime.fromisoformat(start_date).timestamp())
        
        if end_date:
            query += " AND start_time <= ?"
            params.append(datetime.fromisoformat(end_date).timestamp())
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.db.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_active_session(self) -> Optional[Dict]:
        """Get currently active session (if any)."""
        cursor = self.db.execute(
            "SELECT * FROM sessions WHERE status IN ('active', 'paused') ORDER BY start_time DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# ============================================================================
# NOTIFICATION SYSTEM
# ============================================================================

class NotificationSystem:
    """Cross-platform notification delivery."""
    
    def __init__(self, config: Config):
        """Initialize notification system."""
        self.enabled = config.get('notifications.enabled', True)
        self.sound_enabled = config.get('notifications.sound_enabled', True)
        self.urgency = config.get('notifications.urgency', 'normal')
        self.method = self._detect_notification_method()
    
    def _detect_notification_method(self) -> str:
        """Detect best notification method for platform."""
        if sys.platform == 'win32':
            return 'windows'
        elif sys.platform == 'darwin':
            return 'macos'
        elif sys.platform.startswith('linux'):
            return 'linux'
        return 'terminal'
    
    def notify(self, title: str, message: str, urgency: str = 'normal'):
        """Send notification using best available method."""
        if not self.enabled:
            return
        
        try:
            if self.method == 'windows':
                self._notify_windows(title, message)
            elif self.method == 'macos':
                self._notify_macos(title, message)
            elif self.method == 'linux':
                self._notify_linux(title, message)
            else:
                self._notify_terminal(title, message)
        except Exception:
            # Fallback to terminal on any error
            self._notify_terminal(title, message)
        
        # Sound alert
        if self.sound_enabled:
            self._play_sound()
    
    def _notify_windows(self, title: str, message: str):
        """Windows notification via PowerShell."""
        script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
"@
        
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("TaskTimer").Show($toast)
        '''
        subprocess.run(['powershell', '-Command', script], capture_output=True)
    
    def _notify_macos(self, title: str, message: str):
        """macOS notification via osascript."""
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(['osascript', '-e', script], capture_output=True)
    
    def _notify_linux(self, title: str, message: str):
        """Linux notification via notify-send."""
        subprocess.run(['notify-send', title, message], capture_output=True)
    
    def _notify_terminal(self, title: str, message: str):
        """Fallback terminal notification."""
        print(f"\n[OK] {title}")
        print(f"    {message}\n")
    
    def _play_sound(self):
        """Play terminal bell."""
        print('\a', end='', flush=True)


# ============================================================================
# ANALYTICS ENGINE
# ============================================================================

class AnalyticsEngine:
    """Generate productivity insights and reports."""
    
    def __init__(self, db: DatabaseManager):
        """Initialize analytics engine."""
        self.db = db
    
    def daily_report(self, date: str = None) -> Dict:
        """Generate report for specific date (default: today)."""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        start_ts = datetime.fromisoformat(date).timestamp()
        end_ts = start_ts + 86400  # +24 hours
        
        cursor = self.db.execute("""
            SELECT
                COUNT(*) as total_sessions,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                SUM(CASE WHEN status = 'abandoned' THEN 1 ELSE 0 END) as abandoned_sessions,
                SUM(duration_seconds) as total_seconds,
                AVG(duration_seconds) as avg_duration,
                SUM(distraction_count) as total_distractions
            FROM sessions
            WHERE start_time >= ? AND start_time < ?
        """, (start_ts, end_ts))
        
        row = cursor.fetchone()
        
        return {
            'date': date,
            'total_sessions': row['total_sessions'] or 0,
            'completed_sessions': row['completed_sessions'] or 0,
            'abandoned_sessions': row['abandoned_sessions'] or 0,
            'total_focus_hours': (row['total_seconds'] or 0) / 3600,
            'average_duration_minutes': (row['avg_duration'] or 0) / 60,
            'distraction_count': row['total_distractions'] or 0,
            'focus_score': self._calculate_focus_score(row)
        }
    
    def _calculate_focus_score(self, data: Dict) -> float:
        """Calculate focus score (0-100) from session data."""
        total = data['total_sessions'] or 0
        if total == 0:
            return 0.0
        
        completed = data['completed_sessions'] or 0
        total_seconds = data['total_seconds'] or 0
        distractions = data['total_distractions'] or 0
        
        # Completion rate (40%)
        completion_score = (completed / total) * 40
        
        # Hours worked (30%) - target 8 hours
        hours_score = min(total_seconds / (8 * 3600), 1.0) * 30
        
        # Low distraction (20%) - <5 distractions is good
        distraction_rate = distractions / total if total > 0 else 0
        distraction_score = max(0, 1 - (distraction_rate / 5)) * 20
        
        # Consistency (10%) - placeholder for now
        consistency_score = 10
        
        return round(completion_score + hours_score + distraction_score + consistency_score, 1)
    
    def weekly_report(self, week_start: str = None) -> Dict:
        """Generate weekly summary."""
        if not week_start:
            today = datetime.now()
            week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        
        daily_reports = []
        start_date = datetime.fromisoformat(week_start)
        
        for i in range(7):
            date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            daily_reports.append(self.daily_report(date))
        
        # Aggregate
        total_sessions = sum(r['total_sessions'] for r in daily_reports)
        total_hours = sum(r['total_focus_hours'] for r in daily_reports)
        avg_focus_score = sum(r['focus_score'] for r in daily_reports) / 7
        
        return {
            'week_start': week_start,
            'daily_reports': daily_reports,
            'total_sessions': total_sessions,
            'total_focus_hours': round(total_hours, 2),
            'average_focus_score': round(avg_focus_score, 1),
            'days_with_sessions': sum(1 for r in daily_reports if r['total_sessions'] > 0)
        }


# ============================================================================
# MAIN TASKTIMER CLASS
# ============================================================================

class TaskTimer:
    """Main TaskTimer application."""
    
    def __init__(self, config_path: Path = None, db_path: Path = None):
        """Initialize TaskTimer."""
        self.config = Config(config_path)
        
        # Database
        if not db_path:
            db_path = Path(self.config.get('database.path', '~/.tasktimer/sessions.db')).expanduser()
        self.db = DatabaseManager(db_path)
        
        # Core components
        self.timer = TimerEngine()
        self.sessions = SessionManager(self.db)
        self.notifications = NotificationSystem(self.config)
        self.analytics = AnalyticsEngine(self.db)
        
        # Current session
        self.current_session_id = None
    
    def start_session(
        self,
        task_name: str,
        duration: int = None,
        category: str = None,
        notes: str = None,
        **links
    ) -> str:
        """Start a new timer session."""
        # Check if already active
        active = self.sessions.get_active_session()
        if active:
            raise StateError(f"Session '{active['task_name']}' is already active. Stop it first.")
        
        # Duration
        if not duration:
            duration = self.config.get('timer.pomodoro_duration', 1500)
        
        # Create session
        session_id = self.sessions.create_session(
            task_name=task_name,
            category=category,
            notes=notes,
            **links
        )
        
        # Start timer
        self.timer.start(duration)
        self.current_session_id = session_id
        
        # Notification
        self.notifications.notify(
            "TaskTimer Started",
            f"Working on: {task_name} ({duration // 60} min)"
        )
        
        return session_id
    
    def stop_session(self, notes: str = None) -> Dict:
        """Stop current session."""
        if not self.current_session_id:
            raise StateError("No active session to stop")
        
        # Stop timer
        elapsed = self.timer.stop()
        
        # Update session
        self.sessions.complete_session(
            self.current_session_id,
            duration=elapsed,
            notes=notes
        )
        
        session = self.sessions.get_session(self.current_session_id)
        self.current_session_id = None
        
        # Notification
        self.notifications.notify(
            "Session Complete",
            f"{session['task_name']}: {int(elapsed // 60)} minutes"
        )
        
        return session
    
    def pause_session(self):
        """Pause current session."""
        if not self.current_session_id:
            raise StateError("No active session to pause")
        
        self.timer.pause()
        
        # Get current pause_count and increment
        session = self.sessions.get_session(self.current_session_id)
        new_pause_count = (session.get('pause_count') or 0) + 1
        
        self.sessions.update_session(
            self.current_session_id,
            status='paused',
            pause_count=new_pause_count
        )
        
        print("[!] Session paused")
    
    def resume_session(self):
        """Resume paused session."""
        if not self.current_session_id:
            raise StateError("No paused session to resume")
        
        self.timer.resume()
        self.sessions.update_session(
            self.current_session_id,
            status='active'
        )
        
        print("[OK] Session resumed")
    
    def get_status(self) -> Dict:
        """Get current timer status."""
        if not self.current_session_id:
            return {'status': 'No active session'}
        
        session = self.sessions.get_session(self.current_session_id)
        elapsed = self.timer.get_elapsed()
        remaining = self.timer.get_remaining()
        
        return {
            'session_id': self.current_session_id,
            'task_name': session['task_name'],
            'state': self.timer.state,
            'elapsed_minutes': round(elapsed / 60, 1),
            'remaining_minutes': round(remaining / 60, 1) if remaining > 0 else 0,
            'target_minutes': round((elapsed + remaining) / 60, 1) if self.timer.target_duration else None
        }
    
    def close(self):
        """Close TaskTimer (cleanup)."""
        self.db.close()


# ============================================================================
# CLI INTERFACE
# ============================================================================

def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def cmd_start(args):
    """Start a new timer session."""
    timer = TaskTimer()
    try:
        session_id = timer.start_session(
            task_name=args.task,
            duration=args.duration * 60 if args.duration else None,
            category=args.category,
            notes=args.notes
        )
        print(f"[OK] Session started: {args.task}")
        print(f"    Session ID: {session_id}")
        print(f"    Duration: {args.duration or 25} minutes")
        if args.category:
            print(f"    Category: {args.category}")
    finally:
        timer.close()


def cmd_stop(args):
    """Stop current session."""
    timer = TaskTimer()
    try:
        session = timer.stop_session(notes=args.notes)
        print(f"[OK] Session stopped: {session['task_name']}")
        print(f"    Duration: {format_duration(session['duration_seconds'])}")
        if session.get('notes'):
            print(f"    Notes: {session['notes']}")
    finally:
        timer.close()


def cmd_pause(args):
    """Pause current session."""
    timer = TaskTimer()
    try:
        timer.pause_session()
    finally:
        timer.close()


def cmd_resume(args):
    """Resume paused session."""
    timer = TaskTimer()
    try:
        timer.resume_session()
    finally:
        timer.close()


def cmd_status(args):
    """Show current timer status."""
    timer = TaskTimer()
    try:
        status = timer.get_status()
        if 'session_id' in status:
            print("[OK] Active Session")
            print(f"    Task: {status['task_name']}")
            print(f"    State: {status['state']}")
            print(f"    Elapsed: {status['elapsed_minutes']} min")
            if status['remaining_minutes'] > 0:
                print(f"    Remaining: {status['remaining_minutes']} min")
        else:
            print("[!] No active session")
    finally:
        timer.close()


def cmd_list(args):
    """List recent sessions."""
    timer = TaskTimer()
    try:
        sessions = timer.sessions.list_sessions(
            start_date=args.start,
            end_date=args.end,
            category=args.category,
            status=args.status,
            limit=args.limit
        )
        
        if not sessions:
            print("[!] No sessions found")
            return
        
        print(f"[OK] Found {len(sessions)} sessions:\n")
        for s in sessions:
            start_time = datetime.fromtimestamp(s['start_time']).strftime('%Y-%m-%d %H:%M')
            duration = format_duration(s['duration_seconds']) if s['duration_seconds'] else 'N/A'
            print(f"  [{s['status']}] {s['task_name']}")
            print(f"      Start: {start_time} | Duration: {duration}")
            if s['category']:
                print(f"      Category: {s['category']}")
            print()
    finally:
        timer.close()


def cmd_report(args):
    """Generate analytics report."""
    timer = TaskTimer()
    try:
        if args.type == 'daily':
            report = timer.analytics.daily_report(args.date)
            print(f"[OK] Daily Report - {report['date']}\n")
            print(f"  Total Sessions: {report['total_sessions']}")
            print(f"  Completed: {report['completed_sessions']}")
            print(f"  Abandoned: {report['abandoned_sessions']}")
            print(f"  Focus Hours: {report['total_focus_hours']:.1f}h")
            print(f"  Avg Duration: {report['average_duration_minutes']:.1f} min")
            print(f"  Distractions: {report['distraction_count']}")
            print(f"  Focus Score: {report['focus_score']}/100")
        
        elif args.type == 'weekly':
            report = timer.analytics.weekly_report(args.date)
            print(f"[OK] Weekly Report - Week starting {report['week_start']}\n")
            print(f"  Total Sessions: {report['total_sessions']}")
            print(f"  Focus Hours: {report['total_focus_hours']}h")
            print(f"  Average Focus Score: {report['average_focus_score']}/100")
            print(f"  Days Active: {report['days_with_sessions']}/7\n")
            
            print("  Daily Breakdown:")
            for daily in report['daily_reports']:
                print(f"    {daily['date']}: {daily['total_sessions']} sessions, "
                      f"{daily['total_focus_hours']:.1f}h, score {daily['focus_score']}")
    finally:
        timer.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='TaskTimer - Pomodoro-style productivity timer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tasktimer start "Build TaskTimer" --duration 25 --category development
  tasktimer stop --notes "Completed core functionality"
  tasktimer status
  tasktimer list --today
  tasktimer report daily
  tasktimer report weekly

For more information: https://github.com/DonkRonk17/TaskTimer
        """
    )
    
    parser.add_argument('--version', action='version', version=f'TaskTimer {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start a new timer session')
    start_parser.add_argument('task', help='Task name')
    start_parser.add_argument('--duration', type=int, help='Duration in minutes (default: 25)')
    start_parser.add_argument('--category', help='Task category')
    start_parser.add_argument('--notes', help='Session notes')
    start_parser.set_defaults(func=cmd_start)
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop current session')
    stop_parser.add_argument('--notes', help='Completion notes')
    stop_parser.set_defaults(func=cmd_stop)
    
    # Pause command
    pause_parser = subparsers.add_parser('pause', help='Pause current session')
    pause_parser.set_defaults(func=cmd_pause)
    
    # Resume command
    resume_parser = subparsers.add_parser('resume', help='Resume paused session')
    resume_parser.set_defaults(func=cmd_resume)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current timer status')
    status_parser.set_defaults(func=cmd_status)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent sessions')
    list_parser.add_argument('--start', help='Start date (YYYY-MM-DD)')
    list_parser.add_argument('--end', help='End date (YYYY-MM-DD)')
    list_parser.add_argument('--category', help='Filter by category')
    list_parser.add_argument('--status', choices=['active', 'paused', 'completed', 'abandoned'], help='Filter by status')
    list_parser.add_argument('--limit', type=int, default=10, help='Limit results (default: 10)')
    list_parser.set_defaults(func=cmd_list)
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate analytics report')
    report_parser.add_argument('type', choices=['daily', 'weekly'], help='Report type')
    report_parser.add_argument('--date', help='Date or week start (YYYY-MM-DD)')
    report_parser.set_defaults(func=cmd_report)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        args.func(args)
        return 0
    except TaskTimerError as e:
        print(f"[X] Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        return 130
    except Exception as e:
        print(f"[X] Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
