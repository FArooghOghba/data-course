"""Build calendar.ics (a subscribable iCalendar feed) from data/sessions.json.

Every session with a "start" (ISO datetime with timezone) becomes a 2-hour event.
Run: python3 scripts/build_calendar.py  -> writes calendar.ics in the repo root.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DURATION = timedelta(hours=2)


def esc(text):
    # RFC 5545 §3.3.11: escape backslash, ; , and newlines in TEXT values.
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):
    # RFC 5545 §3.1: lines max 75 octets; continuation lines start with a space.
    # Split on characters, not bytes, so Persian (multi-byte) letters never break.
    out, cur = [], ""
    for ch in line:
        if len((cur + ch).encode()) > (75 if not out else 74):
            out.append(cur)
            cur = ""
        cur += ch
    out.append(cur)
    return "\r\n ".join(out)


def utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build(sessions, now):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//data-course//sessions//FA",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:دورهٔ مهندسی داده و هوش مصنوعی",
        "X-WR-TIMEZONE:Asia/Tehran",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for s in sessions:
        if not s.get("start"):
            continue
        start = datetime.fromisoformat(s["start"])
        details = []
        if s.get("speaker"):
            details.append("مدرس: " + s["speaker"])
        if s.get("join"):
            details.append("ورود به کلاس: " + s["join"])
        # UID must stay the same across builds so a changed time updates the
        # event instead of creating a duplicate. Keyed on "type" (e.g. جلسه ۱۱).
        uid = hashlib.sha1(s["type"].encode()).hexdigest()[:16] + "@data-course"
        lines += [
            "BEGIN:VEVENT",
            "UID:" + uid,
            "DTSTAMP:" + utc(now),
            "DTSTART:" + utc(start),
            "DTEND:" + utc(start + DURATION),
            "SUMMARY:" + esc(s["type"] + ": " + s["title"]),
        ]
        if details:
            lines.append("DESCRIPTION:" + esc("\n".join(details)))
        if s.get("join"):
            lines += ["LOCATION:" + esc(s["join"]), "URL:" + s["join"]]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


if __name__ == "__main__":
    sessions = json.loads((ROOT / "data/sessions.json").read_text(encoding="utf-8"))
    ics = build(sessions, datetime.now(timezone.utc))
    # self-check: every physical line fits in 75 octets and events are balanced
    assert all(len(l.encode()) <= 75 for l in ics.split("\r\n")), "line too long"
    assert ics.count("BEGIN:VEVENT") == ics.count("END:VEVENT")
    (ROOT / "calendar.ics").write_text(ics, encoding="utf-8", newline="")
    print(f"calendar.ics: {ics.count('BEGIN:VEVENT')} event(s)")
