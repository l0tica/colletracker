import json
import os
import copy
from constants import TABS

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(DATA_DIR, "profiles.json")


def empty_profile() -> dict:
    return {tab: [] for tab in TABS} | {
        "reward_types": [],
        "item_db": []
    }


def load_profiles() -> dict:
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            _migrate(data)
            return data
        except (json.JSONDecodeError, KeyError):
            pass
    default = {"active": "Default", "profiles": {"Default": empty_profile()}, "window": {}}
    save_profiles(default)
    return default


def _migrate(data: dict):
    for profile in data.get("profiles", {}).values():
        for tab in TABS:
            if tab not in profile:
                profile[tab] = []
        profile.setdefault("reward_types", [])
        profile.setdefault("item_db", [])
        for tab in TABS:
            for col in profile[tab]:
                col.setdefault("active", True)
                col.setdefault("stat_name", "")
                for row in col.get("rows", []):
                    row.setdefault("reward_qty", "")
                    row.setdefault("reward_type", "")
                    row.setdefault("reward_claimed", False)
                    for slot in row.get("slots", []):
                        slot.setdefault("name", "")
                        slot.setdefault("current", 0)


def save_profiles(profiles: dict):
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"Save error: {e}")


def get_active_data(profiles: dict) -> dict:
    return profiles["profiles"][profiles["active"]]


def add_to_list(lst: list, value: str):
    if value and value not in lst:
        lst.append(value)


def calc_pct(collection: dict) -> int:
    total = sum(len(r["slots"]) for r in collection["rows"])
    done = sum(
        1 for r in collection["rows"]
        for s in r["slots"]
        if s["goal"] > 0 and s["current"] >= s["goal"]
    )
    return int(done / total * 100) if total > 0 else 0


def calc_earned_stat(collection: dict) -> float:
    pct = calc_pct(collection)
    best = 0.0
    for ms in collection.get("milestones", []):
        if pct >= ms["pct"]:
            try:
                best = float(ms["value"]) if ms["value"] else 0.0
            except ValueError:
                pass
    return best


def deep_copy_collection(collection: dict) -> dict:
    nc = copy.deepcopy(collection)
    for ms in nc.get("milestones", []):
        ms["claimed"] = False
    for row in nc.get("rows", []):
        row["reward_claimed"] = False
        for slot in row.get("slots", []):
            slot["current"] = 0
    return nc


def build_collection(name, stat, ms_vals, rows) -> dict:
    milestones = [
        {"pct": pct, "value": v, "claimed": False}
        for pct, v in zip([33, 66, 100], ms_vals)
    ]
    return {
        "name": name,
        "stat_name": stat,
        "milestones": milestones,
        "rows": rows,
        "active": True,
    }