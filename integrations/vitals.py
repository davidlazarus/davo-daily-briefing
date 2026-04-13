"""
Fetch VITALS health snapshot for the daily briefing email.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger("briefing-agent")

VITALS_TIMEOUT_S = 3


def _delta(data: dict[str, Any], key: str) -> Any:
    d = data.get(f"{key}_delta")
    if d is not None:
        return d
    nested = data.get("deltas")
    if isinstance(nested, dict):
        return nested.get(key)
    return None


def _num_val(x: Any) -> Any | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, dict):
        return x.get("value") or x.get("current") or x.get("latest")
    return None


def _fmt_delta(d: Any) -> str | None:
    if d is None:
        return None
    try:
        x = float(d)
    except (TypeError, ValueError):
        return None
    if x == 0:
        return "(0)"
    if x < 0:
        av = abs(x)
        s = str(int(av)) if av == int(av) else f"{av:.1f}".rstrip("0").rstrip(".")
        return f"(−{s})"
    s = str(int(x)) if x == int(x) else f"{x:.1f}".rstrip("0").rstrip(".")
    return f"(+{s})"


def _format_rhr(data: dict[str, Any]) -> str | None:
    raw = data.get("resting_hr")
    v = _num_val(raw)
    if v is None:
        return None
    delta_key = None
    if isinstance(raw, dict):
        delta_key = raw.get("delta") or raw.get("delta_vs_baseline")
    if delta_key is None:
        delta_key = _delta(data, "resting_hr")
    part = str(int(v)) if v == int(v) else f"{v:.1f}".rstrip("0").rstrip(".")
    fd = _fmt_delta(delta_key)
    if fd:
        return f"RHR {part} {fd}"
    return f"RHR {part}"


def _format_hrv(data: dict[str, Any]) -> str | None:
    raw = data.get("hrv_ms")
    v = _num_val(raw)
    if v is None:
        return None
    delta_key = _delta(data, "hrv_ms")
    if isinstance(raw, dict):
        delta_key = delta_key or raw.get("delta") or raw.get("delta_vs_baseline")
    part = str(int(round(v)))
    fd = _fmt_delta(delta_key)
    if fd:
        return f"HRV {part} {fd}"
    return f"HRV {part}"


def _format_sleep(data: dict[str, Any]) -> str | None:
    s = data.get("sleep")
    score = data.get("sleep_score")
    if isinstance(s, dict):
        score = s.get("score") or score
        h = s.get("hours") or s.get("h")
        m = s.get("minutes") or s.get("m", 0)
        if h is not None:
            label = f"{int(h)}h{int(m):02d}"
        else:
            label = None
    else:
        label = None

    if label is None and isinstance(s, str) and s.strip():
        label = s.strip()
    if label is None and isinstance(s, (int, float)):
        # interpret as hours (float) or total minutes if large
        if s > 48:  # likely minutes
            total = int(round(s))
            h, m = divmod(total, 60)
            label = f"{h}h{m:02d}"
        else:
            h = int(s)
            frac = s - h
            m = int(round(frac * 60))
            label = f"{h}h{m:02d}"

    if not label:
        return None

    if score is not None:
        try:
            sc = int(float(score))
            return f"Sleep {label} ({sc})"
        except (TypeError, ValueError):
            return f"Sleep {label}"
    return f"Sleep {label}"


def _format_bp(data: dict[str, Any]) -> str | None:
    bp = data.get("bp")
    if bp is None:
        return None
    if isinstance(bp, str) and "/" in bp:
        return f"BP {bp.strip()}"
    if isinstance(bp, (list, tuple)) and len(bp) >= 2:
        return f"BP {int(bp[0])}/{int(bp[1])}"
    if isinstance(bp, dict):
        sys = bp.get("systolic") or bp.get("sys")
        dia = bp.get("diastolic") or bp.get("dia")
        if sys is not None and dia is not None:
            return f"BP {int(sys)}/{int(dia)}"
    return None


def _format_mood(data: dict[str, Any]) -> str | None:
    m = data.get("mood")
    if m is None:
        return None
    if isinstance(m, dict):
        cur = m.get("value") or m.get("score")
        out_of = m.get("out_of") or m.get("scale") or 5
    else:
        cur = m
        out_of = 5
    try:
        c = float(cur)
        o = float(out_of)
    except (TypeError, ValueError):
        return None
    ci = int(c) if c == int(c) else round(c, 1)
    oi = int(o) if o == int(o) else round(o, 1)
    return f"Mood {ci}/{oi}"


def format_vitals_summary(payload: dict[str, Any]) -> str:
    """Turn snapshot JSON into a single compact Health: line."""
    parts: list[str] = []
    for fn in (_format_rhr, _format_hrv, _format_sleep, _format_bp, _format_mood):
        bit = fn(payload)
        if bit:
            parts.append(bit)
    if not parts:
        return ""
    return "Health: " + " · ".join(parts)


def fetch_vitals_summary() -> str | None:
    """
    GET public snapshot from VITALS. Returns formatted line or None on skip/failure.
    """
    base = (os.getenv("VITALS_URL") or "").strip().rstrip("/")
    secret = (os.getenv("VITALS_BRIEFING_SECRET") or "").strip()
    if not base or not secret:
        return None

    url = f"{base}/api/snapshot/public"
    try:
        r = requests.get(
            url,
            headers={"X-Briefing-Secret": secret},
            timeout=VITALS_TIMEOUT_S,
        )
        r.raise_for_status()
        payload = r.json()
    except requests.Timeout:
        logger.warning("VITALS snapshot request timed out after %ss; skipping health block", VITALS_TIMEOUT_S)
        return None
    except requests.RequestException as e:
        logger.warning("VITALS snapshot request failed: %s; skipping health block", e)
        return None
    except ValueError as e:
        logger.warning("VITALS snapshot JSON parse error: %s; skipping health block", e)
        return None

    if not isinstance(payload, dict):
        logger.warning("VITALS snapshot: expected JSON object; skipping health block")
        return None

    line = format_vitals_summary(payload)
    if not line:
        logger.warning("VITALS snapshot: no displayable fields; skipping health block")
        return None
    return line
