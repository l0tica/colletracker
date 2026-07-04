import customtkinter as ctk
from data import add_to_list


class AutocompleteEntry(ctk.CTkFrame):
    def __init__(self, parent, get_items, width=200, placeholder="", on_select=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._get_items = get_items
        self._on_select = on_select
        self._dropdown = None
        self.var = ctk.StringVar()
        self.var.trace_add("write", self._on_type)
        self.entry = ctk.CTkEntry(
            self, width=width, placeholder_text=placeholder, textvariable=self.var)
        self.entry.pack(fill="x")
        self.entry.bind("<FocusOut>", lambda e: self.after(150, self._close))
        self.entry.bind("<Escape>", lambda e: self._close())

    def _on_type(self, *_):
        self._close()
        q = self.var.get().strip().lower()
        if not q:
            return
        matches = [i for i in self._get_items() if q in i.lower()]
        if not matches:
            return
        self.update_idletasks()
        top = self.winfo_toplevel()
        x = self.winfo_rootx() - top.winfo_rootx()
        y = self.winfo_rooty() - top.winfo_rooty() + self.entry.winfo_height()
        w = max(self.entry.winfo_width(), 200)
        self._dropdown = ctk.CTkScrollableFrame(top, height=min(180, len(matches) * 32))
        self._dropdown.place(x=x, y=y, width=w)
        for m in matches:
            ctk.CTkButton(
                self._dropdown, text=m, anchor="w",
                fg_color="transparent", text_color=("black", "white"),
                hover_color=("gray80", "gray30"),
                command=lambda v=m: self._pick(v)
            ).pack(fill="x", pady=1)

    def _pick(self, value):
        self.var.set(value)
        self._close()
        if self._on_select:
            self._on_select(value)

    def _close(self):
        if self._dropdown:
            self._dropdown.destroy()
            self._dropdown = None

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, value: str):
        self.var.set(value)

    def clear(self):
        self.var.set("")


class SlotEditor(ctk.CTkFrame):
    def __init__(self, parent, data: dict, slot: dict = None, on_remove=None):
        super().__init__(parent, fg_color="transparent")
        self._data = data
        self._on_remove = on_remove

        ctk.CTkLabel(self, text="Item:").pack(side="left", padx=(0, 2))
        self._name = AutocompleteEntry(
            self, get_items=lambda: self._data.get("item_db", []),
            width=160, placeholder="Item name")
        self._name.pack(side="left", padx=4)

        ctk.CTkLabel(self, text="Goal:").pack(side="left", padx=(6, 2))
        self._goal = ctk.CTkEntry(self, width=65, placeholder_text="e.g. 125")
        self._goal.pack(side="left", padx=4)

        if slot:
            self._name.set(slot.get("name", ""))
            self._goal.insert(0, str(slot.get("goal", "")))

        ctk.CTkButton(
            self, text="✕", width=28, height=28,
            fg_color="transparent", text_color="gray",
            hover_color=("gray80", "gray30"),
            command=self._remove
        ).pack(side="left", padx=2)

    def _remove(self):
        if self._on_remove:
            self._on_remove(self)
        self.destroy()

    def get(self) -> tuple[str, int]:
        name = self._name.get()
        if name:
            add_to_list(self._data.get("item_db", []), name)
        try:
            goal = int(self._goal.get().strip())
        except ValueError:
            goal = 0
        return name, goal


class RowEditor(ctk.CTkFrame):
    def __init__(self, parent, data: dict, row: dict = None, on_remove=None):
        super().__init__(parent, border_width=1)
        self._data = data
        self._on_remove = on_remove
        self._slot_editors: list[SlotEditor] = []
        self._build(row)

    def _build(self, row: dict = None):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(top, text="Row name:").pack(side="left")
        self._name = ctk.CTkEntry(top, width=150, placeholder_text="Row name (optional)")
        self._name.pack(side="left", padx=6)

        ctk.CTkLabel(top, text="Qty:").pack(side="left", padx=(10, 2))
        self._qty = ctk.CTkEntry(top, width=55, placeholder_text="5")
        self._qty.pack(side="left", padx=2)

        ctk.CTkLabel(top, text="Reward:").pack(side="left", padx=(8, 2))
        self._reward = AutocompleteEntry(
            top, get_items=lambda: self._data.get("reward_types", []),
            width=150, placeholder="e.g. Topaz Gem")
        self._reward.pack(side="left", padx=4)

        if row:
            self._name.insert(0, row.get("name", ""))
            self._qty.insert(0, str(row.get("reward_qty", "")))
            self._reward.set(row.get("reward_type", ""))

        if self._on_remove:
            ctk.CTkButton(
                top, text="Remove row", width=90, height=26,
                fg_color="transparent", border_width=1, text_color="gray",
                command=self._remove
            ).pack(side="right", padx=8)

        self._slots_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._slots_frame.pack(fill="x", padx=8, pady=4)

        if row:
            for slot in row.get("slots", []):
                self._add_slot(slot)

        ctk.CTkButton(
            self, text="+ Add item slot", width=120, height=26,
            command=self._add_slot
        ).pack(anchor="w", padx=8, pady=(0, 8))

    def _remove(self):
        if self._on_remove:
            self._on_remove(self)
        self.destroy()

    def _add_slot(self, slot: dict = None):
        def on_remove(se):
            if se in self._slot_editors:
                self._slot_editors.remove(se)
        se = SlotEditor(self._slots_frame, self._data, slot=slot, on_remove=on_remove)
        se.pack(fill="x", pady=2)
        self._slot_editors.append(se)

    def get(self) -> dict:
        rtype = self._reward.get()
        if rtype:
            add_to_list(self._data.get("reward_types", []), rtype)
        slots = []
        for se in self._slot_editors:
            name, goal = se.get()
            if goal > 0:
                slots.append({"name": name, "goal": goal, "current": 0})
        return {
            "name": self._name.get().strip(),
            "reward_qty": self._qty.get().strip(),
            "reward_type": rtype,
            "reward_claimed": False,
            "slots": slots,
        }


class CollectionListItem(ctk.CTkFrame):
    def __init__(self, parent, name: str, pct: int, active: bool, on_click):
        super().__init__(parent, fg_color="transparent")
        from constants import pct_color
        color = pct_color(pct)
        text_color = ("black", "white") if active else ("gray", "gray")
        label = f"{'○ ' if not active else ''}{name}"

        ctk.CTkButton(
            self, text=label, anchor="w",
            fg_color="transparent", text_color=text_color,
            hover_color=("gray85", "gray25"),
            command=on_click
        ).pack(fill="x")

        bar_bg = ctk.CTkFrame(self, height=5, fg_color=("gray80", "gray30"), corner_radius=2)
        bar_bg.pack(fill="x", padx=4, pady=(0, 2))
        if pct > 0:
            ctk.CTkFrame(
                bar_bg, height=5, fg_color=color, corner_radius=2
            ).place(x=0, y=0, relwidth=pct / 100, relheight=1)

        ctk.CTkLabel(
            self, text=f"{pct}%", text_color=color,
            font=ctk.CTkFont(size=11), anchor="e"
        ).pack(fill="x", padx=8)