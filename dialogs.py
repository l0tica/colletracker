import customtkinter as ctk
import copy
from tkinter import messagebox
from data import (empty_profile, save_profiles, deep_copy_collection,
                  build_collection, add_to_list, get_active_data)
from widgets import RowEditor, AutocompleteEntry
from constants import TABS


class AddCollectionDialog(ctk.CTkToplevel):
    def __init__(self, parent, data: dict, callback, existing: dict = None):
        super().__init__(parent)
        self.title("Edit Collection" if existing else "Add Collection")
        self.geometry("800x740")
        self.resizable(True, True)
        self._data = data
        self._callback = callback
        self._existing = existing
        self._row_editors: list[RowEditor] = []
        self.grab_set()
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(scroll, text="Collection name").pack(anchor="w")
        self._name = ctk.CTkEntry(scroll, width=440)
        self._name.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text="Finish stat name (e.g. Defense Rate)").pack(anchor="w")
        self._stat = ctk.CTkEntry(scroll, width=320)
        self._stat.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(
            scroll,
            text="Milestone values — cumulative stat total at each milestone",
            text_color="gray", font=ctk.CTkFont(size=12)
        ).pack(anchor="w", pady=(4, 2))

        ms_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ms_frame.pack(anchor="w", pady=(0, 12))
        self._ms_entries = []
        for i, label in enumerate(["33%", "66%", "100%"]):
            ctk.CTkLabel(ms_frame, text=label).grid(row=0, column=i * 2, padx=(12, 4))
            e = ctk.CTkEntry(ms_frame, width=90, placeholder_text="e.g. 9")
            e.grid(row=0, column=i * 2 + 1, padx=4)
            self._ms_entries.append(e)

        ctk.CTkLabel(scroll, text="Rows", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(8, 4))
        ctk.CTkButton(scroll, text="+ Add row", command=self._add_row).pack(anchor="w", pady=(0, 6))
        self._rows_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._rows_frame.pack(fill="x")

        ctk.CTkButton(
            scroll, text="Save collection",
            fg_color="#1D9E75", hover_color="#0F6E56",
            command=self._save
        ).pack(anchor="w", pady=12)

        if self._existing:
            self._populate_existing()

    def _populate_existing(self):
        ex = self._existing
        self._name.insert(0, ex["name"])
        self._stat.insert(0, ex.get("stat_name", ""))
        for i, ms in enumerate(ex.get("milestones", [])):
            if i < len(self._ms_entries):
                self._ms_entries[i].insert(0, ms.get("value", ""))
        for row in ex.get("rows", []):
            self._add_row(row)

    def _add_row(self, row: dict = None):
        def on_remove(re):
            if re in self._row_editors:
                self._row_editors.remove(re)

        re = RowEditor(self._rows_frame, self._data, row=row, on_remove=on_remove)
        re.pack(fill="x", pady=4)

        if row is None:
            self._row_editors.insert(0, re)
            for w in self._rows_frame.winfo_children():
                w.pack_forget()
            for ed in self._row_editors:
                ed.pack(fill="x", pady=4)
        else:
            self._row_editors.append(re)

    def _save(self):
        name = self._name.get().strip()
        stat = self._stat.get().strip()
        if not name:
            return

        ms_vals = [e.get().strip() for e in self._ms_entries]
        rows = [re.get() for re in self._row_editors]

        if self._existing:
            milestones = self._existing["milestones"]
            for i, v in enumerate(ms_vals):
                if i < len(milestones):
                    milestones[i]["value"] = v
            for i, row in enumerate(rows):
                if i < len(self._existing["rows"]):
                    orig = self._existing["rows"][i]
                    row["reward_claimed"] = orig.get("reward_claimed", False)
                    for j, slot in enumerate(row["slots"]):
                        if j < len(orig["slots"]):
                            slot["current"] = orig["slots"][j].get("current", 0)
            collection = {
                "name": name, "stat_name": stat,
                "milestones": milestones, "rows": rows,
                "active": self._existing.get("active", True)
            }
        else:
            collection = build_collection(name, stat, ms_vals, rows)

        self._callback(collection)
        self.destroy()


class ProfileDialog(ctk.CTkToplevel):
    def __init__(self, parent, profiles: dict, on_done):
        super().__init__(parent)
        self.title("Manage Profiles")
        self.geometry("440x540")
        self.resizable(False, False)
        self._profiles = profiles
        self._on_done = on_done
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Profiles", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(16, 8))

        self._list_frame = ctk.CTkScrollableFrame(self, height=200)
        self._list_frame.pack(fill="x", padx=16)
        self._populate_list()

        ctk.CTkLabel(self, text="New profile name").pack(pady=(16, 4))
        self._new_name = ctk.CTkEntry(self, width=300)
        self._new_name.pack()

        ctk.CTkButton(self, text="Create empty profile",
                      command=self._create_empty).pack(pady=6)

        ctk.CTkLabel(self, text="Import collections from:").pack(pady=(10, 4))
        names = list(self._profiles["profiles"].keys())
        self._import_var = ctk.StringVar(value=names[0] if names else "")
        self._import_combo = ctk.CTkComboBox(
            self, values=names, variable=self._import_var, width=300)
        self._import_combo.pack()

        ctk.CTkButton(
            self, text="Create with imported collections (progress reset)",
            command=self._create_import
        ).pack(pady=6)

    def _populate_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        for name in self._profiles["profiles"]:
            active = name == self._profiles["active"]
            row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text=("● " if active else "  ") + name,
                text_color="#1D9E75" if active else ("white", "black")
            ).pack(side="left", padx=8)
            if not active:
                ctk.CTkButton(row, text="Switch", width=70, height=26,
                              command=lambda n=name: self._switch(n)).pack(side="right", padx=4)
                ctk.CTkButton(
                    row, text="Delete", width=70, height=26,
                    fg_color="transparent", border_width=1, text_color="gray",
                    command=lambda n=name: self._delete(n)
                ).pack(side="right", padx=4)

    def _create_empty(self):
        name = self._new_name.get().strip()
        if not name or name in self._profiles["profiles"]:
            return
        self._profiles["profiles"][name] = empty_profile()
        self._profiles["active"] = name
        save_profiles(self._profiles)
        self._on_done()
        self.destroy()

    def _create_import(self):
        name = self._new_name.get().strip()
        src = self._import_var.get()
        if not name or name in self._profiles["profiles"]:
            return
        if src not in self._profiles["profiles"]:
            return
        src_data = self._profiles["profiles"][src]
        new_data = empty_profile()
        new_data["item_db"] = copy.deepcopy(src_data.get("item_db", []))
        new_data["reward_types"] = copy.deepcopy(src_data.get("reward_types", []))
        for tab in TABS:
            new_data[tab] = [deep_copy_collection(c) for c in src_data.get(tab, [])]
        self._profiles["profiles"][name] = new_data
        self._profiles["active"] = name
        save_profiles(self._profiles)
        self._on_done()
        self.destroy()

    def _switch(self, name: str):
        self._profiles["active"] = name
        save_profiles(self._profiles)
        self._on_done()
        self.destroy()

    def _delete(self, name: str):
        if not messagebox.askyesno("Delete profile",
                                   f"Delete '{name}'? This cannot be undone."):
            return
        del self._profiles["profiles"][name]
        save_profiles(self._profiles)
        self._populate_list()
        names = list(self._profiles["profiles"].keys())
        self._import_combo.configure(values=names)