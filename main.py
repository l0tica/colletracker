import customtkinter as ctk
import csv
from tkinter import filedialog, messagebox
from data import load_profiles, save_profiles, get_active_data
from dialogs import ProfileDialog
from tabs.collection_tab import CollectionTab
from tabs.items_tab import ItemsTab
from tabs.overall_tab import OverallTab
from constants import APP_NAME, APP_VERSION, TABS

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._profiles = load_profiles()
        self._collection_tabs: dict[str, CollectionTab] = {}
        self._items_tab: ItemsTab = None
        self._overall_tab: OverallTab = None
        self._load_window_state()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    def _data(self):
        return get_active_data(self._profiles)

    def _load_window_state(self):
        state = self._profiles.get("window", {})
        w = state.get("width", 1100)
        h = state.get("height", 750)
        x = state.get("x", 100)
        y = state.get("y", 100)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _save_window_state(self):
        self._profiles["window"] = {
            "width": self.winfo_width(),
            "height": self.winfo_height(),
            "x": self.winfo_x(),
            "y": self.winfo_y(),
        }

    def _on_close(self):
        self._save_window_state()
        save_profiles(self._profiles)
        self.destroy()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self._collection_tabs.clear()
        self.title(f"{APP_NAME} v{APP_VERSION} — {self._profiles['active']}")
        self._build_topbar()
        self._build_tabs()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, height=46)
        bar.pack(fill="x", padx=12, pady=(8, 0))
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="Profile:").pack(side="left", padx=(10, 4))
        self._profile_var = ctk.StringVar(value=self._profiles["active"])
        ctk.CTkComboBox(
            bar,
            values=list(self._profiles["profiles"].keys()),
            variable=self._profile_var,
            width=200,
            command=self._switch_profile
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            bar, text="Manage profiles", width=140,
            command=self._open_profile_dialog
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            bar, text="Light / Dark", width=110,
            command=self._toggle_mode
        ).pack(side="right", padx=4)
        ctk.CTkButton(
            bar, text="Export incomplete", width=140,
            command=lambda: self._export(only_incomplete=True)
        ).pack(side="right", padx=4)
        ctk.CTkButton(
            bar, text="Export all", width=90,
            command=lambda: self._export(only_incomplete=False)
        ).pack(side="right", padx=4)

    def _build_tabs(self):
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=12, pady=8)

        for tab in TABS:
            self._tabview.add(tab)
            ct = CollectionTab(
                self._tabview.tab(tab), tab,
                get_profiles=lambda: self._profiles,
                save_cb=self._save,
                refresh_all_cb=self._refresh_all
            )
            ct.pack(fill="both", expand=True)
            self._collection_tabs[tab] = ct

        self._tabview.add("Items")
        self._items_tab = ItemsTab(
            self._tabview.tab("Items"),
            get_profiles=lambda: self._profiles,
            save_cb=self._save,
            refresh_all_cb=self._refresh_all
        )
        self._items_tab.pack(fill="both", expand=True)

        self._tabview.add("Overall Stats")
        self._overall_tab = OverallTab(
            self._tabview.tab("Overall Stats"),
            get_profiles=lambda: self._profiles
        )
        self._overall_tab.pack(fill="both", expand=True)

    def _save(self):
        save_profiles(self._profiles)

    def _refresh_all(self):
        for ct in self._collection_tabs.values():
            ct.refresh_list()
        if self._overall_tab:
            self._overall_tab.build()
        if self._items_tab:
            self._items_tab.refresh()

    def _switch_profile(self, name: str):
        self._profiles["active"] = name
        save_profiles(self._profiles)
        self._build_ui()

    def _open_profile_dialog(self):
        ProfileDialog(self, self._profiles, on_done=self._build_ui)

    def _toggle_mode(self):
        mode = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if mode == "Dark" else "dark")

    def _export(self, only_incomplete: bool = False):
        data = self._data()
        label = "incomplete" if only_incomplete else "all"
        profile = self._profiles["active"]
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"cabal_{label}_{profile}.csv"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Tab", "Collection", "Progress %",
                    "Row", "Item", "Current", "Goal", "Remaining"
                ])
                for tab in TABS:
                    for col in data.get(tab, []):
                        from data import calc_pct
                        pct = calc_pct(col)
                        for row in col["rows"]:
                            for slot in row["slots"]:
                                remaining = max(0, slot["goal"] - slot["current"])
                                if only_incomplete and remaining == 0:
                                    continue
                                writer.writerow([
                                    tab, col["name"], f"{pct}%",
                                    row.get("name", ""),
                                    slot.get("name", ""),
                                    slot["current"], slot["goal"], remaining
                                ])
            messagebox.showinfo("Export complete", f"Saved to:\n{path}")
        except OSError as e:
            messagebox.showerror("Export failed", str(e))


if __name__ == "__main__":
    App().mainloop()