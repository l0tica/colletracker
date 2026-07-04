APP_NAME = "Cabal Collection Tracker"
APP_VERSION = "2.0"
TABS = ["Dungeon", "World", "Special", "Boss"]

COLORS = {
    "green_dark":  "#2d6a4f",
    "green":       "#1D9E75",
    "green_light": "#0F6E56",
    "orange":      "#BA7517",
    "gray":        "gray",
    "danger":      "#c0392b",
    "danger_hover":"#922b21",
}

def pct_color(pct: int) -> str:
    if pct == 100:
        return COLORS["green_dark"]
    if pct >= 66:
        return COLORS["green"]
    if pct >= 33:
        return COLORS["orange"]
    return COLORS["gray"]