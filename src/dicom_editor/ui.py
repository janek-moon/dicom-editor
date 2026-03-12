from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .dicom_io import discover_dicom_files, group_by_set, read_dataset, write_dataset
from .edit_ops import EditOperation, EditOpsEngine
from .module_requirements import ModuleRequirementsEngine
from .tag_model import TagRow, dataset_to_rows, parse_tag
from .tag_registry import CRITICAL_DELETE_WARNING_TAGS, DEFAULT_REMOTE_URL, TagRegistry

TAG_VALUE_PRESETS = {
    "300E0002": ["APPROVED", "UNAPPROVED", "REJECTED"],  # Approval Status
}


@dataclass
class GroupState:
    key: str
    paths: List[Path]
    operations: List[EditOperation]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DICOM Tag Editor")
        self.resize(1320, 780)

        self.registry = TagRegistry()
        self.engine = EditOpsEngine(self.registry)
        self.module_engine = ModuleRequirementsEngine(self.registry)

        self.groups: Dict[str, GroupState] = {}
        self.current_group_key: str | None = None
        self.current_rows: List[TagRow] = []
        self.add_mode = False

        self._build_ui()
        self._apply_styles()
        if DEFAULT_REMOTE_URL:
            self._append_log(f"Remote allowlist URL configured: {DEFAULT_REMOTE_URL}")

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top_row = QHBoxLayout()
        self.btn_load_file = QPushButton("Load DICOM File")
        self.btn_load_folder = QPushButton("Load Folder")
        self.group_combo = QComboBox()
        self.group_combo.setMinimumWidth(500)
        self.btn_save = QPushButton("Save Edited Files")

        top_row.addWidget(self.btn_load_file)
        top_row.addWidget(self.btn_load_folder)
        top_row.addWidget(QLabel("Set:"))
        top_row.addWidget(self.group_combo, 1)
        top_row.addWidget(self.btn_save)
        layout.addLayout(top_row)

        content = QGridLayout()
        layout.addLayout(content, 1)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Path", "Tag", "Name", "VR", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        content.addWidget(self.table, 0, 0)

        side = QWidget()
        side_layout = QVBoxLayout(side)

        form = QFormLayout()
        self.input_path = QComboBox()
        self.input_path.setEditable(True)
        self.input_path.setInsertPolicy(QComboBox.NoInsert)
        self.input_path.setMinimumWidth(420)
        self.input_path.setMinimumHeight(34)

        self.input_tag = QComboBox()
        self.input_tag.setEditable(True)
        self.input_tag.setInsertPolicy(QComboBox.NoInsert)
        self.input_tag.setMinimumWidth(420)
        self.input_tag.setMinimumHeight(34)
        self._tag_model = QStringListModel(self)
        self._tag_completer = QCompleter(self._tag_model, self)
        self._tag_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._tag_completer.setFilterMode(Qt.MatchContains)
        self.input_tag.setCompleter(self._tag_completer)
        self.input_vr = QLineEdit()
        self.input_vr.setMinimumHeight(34)

        self.input_value = QComboBox()
        self.input_value.setEditable(True)
        self.input_value.setInsertPolicy(QComboBox.NoInsert)
        self.input_value.setMinimumWidth(420)
        self.input_value.setMinimumHeight(34)

        form.addRow("Path", self.input_path)
        form.addRow("Tag", self.input_tag)
        form.addRow("VR", self.input_vr)
        form.addRow("Value", self.input_value)
        side_layout.addLayout(form)

        add_mode_row = QHBoxLayout()
        self.btn_start_add = QPushButton("Start Add")
        self.btn_start_add.setCheckable(True)
        self.btn_start_add.setMinimumHeight(34)
        add_mode_row.addWidget(self.btn_start_add)
        side_layout.addLayout(add_mode_row)

        actions = QHBoxLayout()
        self.btn_update = QPushButton("Update Selected")
        self.btn_update.setEnabled(False)
        self.btn_add = QPushButton("Confirm Add")
        self.btn_add.setEnabled(False)
        self.btn_remove = QPushButton("Remove Selected")
        actions.addWidget(self.btn_update)
        actions.addWidget(self.btn_add)
        actions.addWidget(self.btn_remove)
        side_layout.addLayout(actions)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        side_layout.addWidget(QLabel("Log"))
        side_layout.addWidget(self.log, 1)

        content.addWidget(side, 0, 1)
        content.setColumnStretch(0, 4)
        content.setColumnStretch(1, 2)

        self.btn_load_file.clicked.connect(self.on_load_file)
        self.btn_load_folder.clicked.connect(self.on_load_folder)
        self.group_combo.currentIndexChanged.connect(self.on_group_changed)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        self.btn_update.clicked.connect(self.on_update)
        self.btn_start_add.clicked.connect(self.on_start_add)
        self.btn_add.clicked.connect(self.on_add)
        self.btn_remove.clicked.connect(self.on_remove)
        self.btn_save.clicked.connect(self.on_save)
        self.input_path.currentTextChanged.connect(self.on_path_changed)
        self.input_tag.currentTextChanged.connect(self.on_tag_changed)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0b1220;
                color: #d8e1ee;
                font-family: "Avenir Next", "Pretendard", "Helvetica Neue", sans-serif;
                font-size: 13px;
            }
            QLabel {
                color: #9fb0c6;
                font-weight: 600;
            }
            QPushButton {
                background-color: #2f81f7;
                color: #ffffff;
                border: 0;
                border-radius: 10px;
                padding: 9px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #236ad0;
            }
            QPushButton:pressed {
                background-color: #1d56a9;
            }
            QPushButton:checked {
                background-color: #d29922;
                color: #0b1220;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #111a2b;
                color: #d8e1ee;
                border: 1px solid #2a3a53;
                border-radius: 10px;
                padding: 6px 10px;
                selection-background-color: #25436b;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #2f81f7;
            }
            QComboBox::drop-down {
                width: 26px;
                border-left: 1px solid #2a3a53;
                background-color: #1a2740;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            QTableWidget {
                background-color: #111a2b;
                border: 1px solid #2a3a53;
                border-radius: 12px;
                gridline-color: #1e2c42;
                selection-background-color: #274a73;
                selection-color: #f3f7fd;
            }
            QHeaderView::section {
                background-color: #182338;
                color: #b8c7da;
                padding: 8px;
                border: 0;
                border-bottom: 1px solid #2a3a53;
                font-weight: 700;
            }
            QTextEdit {
                background-color: #0a101b;
                color: #c8d8ec;
                border: 1px solid #223149;
            }
            """
        )

    def _append_log(self, message: str) -> None:
        self.log.append(message)

    def _set_groups(self, groups: Dict[str, List[Path]]) -> None:
        self.groups.clear()
        self.group_combo.clear()

        for key, paths in groups.items():
            self.groups[key] = GroupState(key=key, paths=paths, operations=[])
            self.group_combo.addItem(f"{key} ({len(paths)} files)", userData=key)

        if self.group_combo.count() > 0:
            self.group_combo.setCurrentIndex(0)
            self.on_group_changed(0)

    def _current_group(self) -> GroupState | None:
        if not self.current_group_key:
            return None
        return self.groups.get(self.current_group_key)

    def _refresh_table(self) -> None:
        g = self._current_group()
        if not g or not g.paths:
            self.table.setRowCount(0)
            self.current_rows = []
            self.input_path.clear()
            self.input_value.clear()
            self.btn_update.setEnabled(False)
            self._set_add_mode(False)
            return

        ds = read_dataset(g.paths[0])
        self.engine.apply_all(ds, g.operations)
        rows = dataset_to_rows(ds)
        self.current_rows = rows

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row.path))
            self.table.setItem(r, 1, QTableWidgetItem(row.tag))
            self.table.setItem(r, 2, QTableWidgetItem(row.name))
            self.table.setItem(r, 3, QTableWidgetItem(row.vr))
            self.table.setItem(r, 4, QTableWidgetItem(row.value))
        self.table.setSortingEnabled(True)

        self.table.resizeColumnsToContents()
        self._refresh_path_select(rows)
        self.btn_update.setEnabled(self.table.currentRow() >= 0)

    def on_start_add(self) -> None:
        if self.add_mode:
            self._set_add_mode(False)
            self._append_log("Add mode canceled")
            return

        if not self._current_group():
            QMessageBox.warning(self, "Add setup failed", "Load a DICOM file or folder first.")
            self.btn_start_add.setChecked(False)
            return
        self._set_add_mode(True)
        self.table.clearSelection()
        self.btn_update.setEnabled(False)
        self.input_path.setCurrentText("")
        self.input_tag.setCurrentText("")
        self.input_vr.clear()
        self.input_value.setCurrentText("")
        self._append_log("Add mode enabled: fill fields and press Confirm Add")

    def _set_add_mode(self, enabled: bool) -> None:
        self.add_mode = enabled
        self.btn_add.setEnabled(enabled)
        self.btn_start_add.setText("Cancel Add" if enabled else "Start Add")
        self.btn_start_add.setChecked(enabled)

    def _refresh_path_select(self, rows: List[TagRow]) -> None:
        current = self.input_path.currentText().strip()
        self.input_path.blockSignals(True)
        self.input_path.clear()
        for row in rows:
            self.input_path.addItem(row.path)
        self.input_path.blockSignals(False)
        if current:
            self.input_path.setCurrentText(current)
        elif self.input_path.count() > 0:
            self.input_path.setCurrentIndex(0)
        self._refresh_value_select_for_path(self.input_path.currentText())
        self._refresh_tag_select(rows)

    def _refresh_tag_select(self, rows: List[TagRow]) -> None:
        current = self.input_tag.currentText().strip()
        choices: list[str] = []
        seen: set[str] = set()

        # Show current dataset tags first.
        for row in rows:
            key = row.tag
            if key in seen:
                continue
            seen.add(key)
            choices.append(f"{row.name} {key}")

        # Add standard allowlist tags for add-mode discoverability.
        for meta in self.registry.all_meta():
            tag_text = f"({meta.tag >> 16:04X},{meta.tag & 0xFFFF:04X})"
            choice = f"{meta.keyword} {tag_text}"
            if choice in seen:
                continue
            seen.add(choice)
            choices.append(choice)

        self.input_tag.blockSignals(True)
        self.input_tag.clear()
        self.input_tag.addItems(choices)
        self.input_tag.blockSignals(False)
        self._tag_model.setStringList(choices)

        if current:
            self.input_tag.setCurrentText(current)
        elif self.input_tag.count() > 0:
            self.input_tag.setCurrentIndex(0)

    def _normalize_tag_text(self, tag_text: str) -> str:
        m = re.search(r"\(?([0-9A-Fa-f]{4})[, ]?([0-9A-Fa-f]{4})\)?", tag_text.strip())
        if not m:
            return ""
        return f"{m.group(1)}{m.group(2)}".upper()

    def _path_matches_tag(self, path_text: str, normalized_tag: str) -> bool:
        if not path_text or len(normalized_tag) != 8:
            return False
        m = re.search(r"([0-9A-Fa-f]{8})(?:\[\d+\])?$", path_text.strip())
        if not m:
            return False
        return m.group(1).upper() == normalized_tag

    def _paths_for_tag(self, tag_text: str) -> list[str]:
        normalized = self._normalize_tag_text(tag_text)
        if len(normalized) != 8:
            return []

        paths: list[str] = []
        for row in self.current_rows:
            row_tag = row.tag.strip().upper().replace("(", "").replace(")", "").replace(",", "")
            if row_tag == normalized:
                paths.append(row.path)
        return sorted(set(paths))

    def _refresh_path_candidates_for_tag(self, tag_text: str) -> None:
        previous = self.input_path.currentText().strip()
        candidates = self._paths_for_tag(tag_text)

        self.input_path.blockSignals(True)
        self.input_path.clear()
        for p in candidates:
            self.input_path.addItem(p)

        if not candidates:
            # For add-mode, default to root-level selected tag.
            normalized_tag = self._normalize_tag_text(tag_text)
            self.input_path.setCurrentText(normalized_tag or previous)
        elif len(candidates) == 1:
            self.input_path.setCurrentText(candidates[0])
        elif previous and previous in candidates:
            self.input_path.setCurrentText(previous)
        else:
            self.input_path.setCurrentIndex(0)
        self.input_path.blockSignals(False)

    def _refresh_value_select_for_tag(self, tag_text: str) -> None:
        normalized = self._normalize_tag_text(tag_text)
        current_value = self.input_value.currentText().strip()
        self.input_value.clear()
        if len(normalized) != 8:
            return

        values: list[str] = []
        for row in self.current_rows:
            row_tag = row.tag.strip().upper().replace("(", "").replace(")", "").replace(",", "")
            if row_tag == normalized:
                values.append(row.value)

        seen = set()
        source_values = sorted(values)
        preset_values = TAG_VALUE_PRESETS.get(normalized, [])
        if preset_values:
            source_values = sorted(set(source_values).union(preset_values))

        for v in source_values:
            if v in seen:
                continue
            seen.add(v)
            self.input_value.addItem(v)

        if current_value and current_value in seen:
            self.input_value.setCurrentText(current_value)
        elif self.input_value.count() > 0:
            self.input_value.setCurrentIndex(0)

    def _refresh_value_select_for_path(self, path_text: str) -> None:
        current_value = self.input_value.currentText().strip()
        self.input_value.clear()

        values = [row.value for row in self.current_rows if row.path == path_text]

        seen = set()
        for v in sorted(values):
            if v in seen:
                continue
            seen.add(v)
            self.input_value.addItem(v)

        if current_value:
            self.input_value.setCurrentText(current_value)
        elif self.input_value.count() > 0:
            self.input_value.setCurrentIndex(0)

    def on_path_changed(self, text: str) -> None:
        self._refresh_value_select_for_path(text)

    def on_tag_changed(self, text: str) -> None:
        self._refresh_path_candidates_for_tag(text)
        self._refresh_value_select_for_tag(text)
        normalized = self._normalize_tag_text(text)
        if len(normalized) == 8:
            vr = self.registry.get_vr(int(normalized, 16))
            if vr:
                self.input_vr.setText(vr)

    def on_load_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Choose DICOM file")
        if not path_str:
            return
        p = Path(path_str)
        groups = {f"single|{p.name}": [p]}
        self._set_groups(groups)
        self._append_log(f"Loaded single file: {p}")

    def on_load_folder(self) -> None:
        folder_str = QFileDialog.getExistingDirectory(self, "Choose folder")
        if not folder_str:
            return
        folder = Path(folder_str)
        records, failed = discover_dicom_files(folder)
        groups = group_by_set(records)
        self._set_groups(groups)
        self._append_log(f"Loaded folder: {folder} / groups={len(groups)}")
        if failed:
            self._append_log(f"Failed files: {len(failed)}")
            for fp, err in failed[:10]:
                self._append_log(f"- {fp}: {err}")

    def on_group_changed(self, _: int) -> None:
        key = self.group_combo.currentData()
        self.current_group_key = str(key) if key else None
        self._set_add_mode(False)
        self._refresh_table()

    def on_row_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.btn_update.setEnabled(False)
            return
        self._set_add_mode(False)
        self.btn_update.setEnabled(True)
        path = self.table.item(row, 0).text()
        tag = self.table.item(row, 1).text()
        name = self.table.item(row, 2).text()
        vr = self.table.item(row, 3).text()
        value = self.table.item(row, 4).text()
        self.input_path.setCurrentText(path)
        self.input_tag.setCurrentText(f"{name} {tag}")
        self.input_vr.setText(vr)
        self.input_value.setCurrentText(value)

    def _build_operation(self, op: str) -> EditOperation:
        normalized_tag = self._normalize_tag_text(self.input_tag.currentText())
        tag_int = parse_tag(normalized_tag)
        vr_text = self.input_vr.text().strip() or None
        value_text = self.input_value.currentText().strip() or None
        path_text = self.input_path.currentText().strip() or None
        if op == "add":
            # Default add target is root-level selected tag.
            # Only keep user-entered nested path when its final segment already matches the selected tag.
            if not path_text or not self._path_matches_tag(path_text, normalized_tag):
                path_text = normalized_tag
        return EditOperation(op=op, tag=tag_int, vr=vr_text, value=value_text, path=path_text)

    def _build_update_operation_from_selected(self) -> EditOperation:
        row = self.table.currentRow()
        if row < 0:
            raise ValueError("Update is available only after selecting an existing row in the table.")
        row_path = self.table.item(row, 0).text().strip()
        row_tag = self.table.item(row, 1).text().strip()
        row_vr = self.table.item(row, 3).text().strip()

        tag_int = parse_tag(row_tag)
        vr_text = self.input_vr.text().strip() or row_vr or None
        value_text = self.input_value.currentText().strip() or None
        return EditOperation(op="update", tag=tag_int, vr=vr_text, value=value_text, path=row_path)

    def _apply_and_record(self, op: EditOperation) -> None:
        g = self._current_group()
        if not g:
            raise ValueError("Load a DICOM file or folder first.")

        preview_ds = read_dataset(g.paths[0])
        self.engine.apply_all(preview_ds, g.operations + [op])
        g.operations.append(op)
        self._refresh_table()

    def on_update(self) -> None:
        try:
            op = self._build_update_operation_from_selected()
            self._apply_and_record(op)
            self._append_log(f"Updated tag {op.tag:08X} @ {op.path or 'root'}")
        except Exception as exc:
            QMessageBox.warning(self, "Update failed", str(exc))

    def on_add(self) -> None:
        try:
            if not self.add_mode:
                raise ValueError("Click 'Start Add' first, then fill fields and press 'Confirm Add'.")
            op = self._build_operation("add")
            self._apply_and_record(op)
            self._append_log(f"Added tag {op.tag:08X} @ {op.path or 'root'}")

            g = self._current_group()
            if g:
                preview_ds = read_dataset(g.paths[0])
                self.engine.apply_all(preview_ds, g.operations)
                auto_result = self.module_engine.suggest_required_ops(preview_ds, op.tag)
                if auto_result.ops:
                    for auto_op in auto_result.ops:
                        self._apply_and_record(auto_op)
                    module_label = ", ".join(auto_result.modules[:5])
                    suffix = "" if len(auto_result.modules) <= 5 else " ..."
                    self._append_log(
                        f"Auto-added {len(auto_result.ops)} required tags from module(s): {module_label}{suffix}"
                    )
            self._set_add_mode(False)
        except Exception as exc:
            QMessageBox.warning(self, "Add failed", str(exc))

    def on_remove(self) -> None:
        try:
            op = self._build_operation("remove")
            if op.tag in CRITICAL_DELETE_WARNING_TAGS:
                answer = QMessageBox.question(
                    self,
                    "Confirm critical deletion",
                    "This tag is critical. Delete anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
            self._apply_and_record(op)
            self._append_log(f"Removed tag {op.tag:08X} @ {op.path or 'root'}")
        except Exception as exc:
            QMessageBox.warning(self, "Remove failed", str(exc))

    def on_save(self) -> None:
        g = self._current_group()
        if not g:
            QMessageBox.warning(self, "Save failed", "No files loaded")
            return

        out_dir_str = QFileDialog.getExistingDirectory(self, "Choose output directory")
        if not out_dir_str:
            return
        out_dir = Path(out_dir_str)

        saved = 0
        failed = 0
        for src in g.paths:
            try:
                ds = read_dataset(src)
                self.engine.apply_all(ds, g.operations)
                out_path = out_dir / f"edited_{src.name}"
                write_dataset(ds, out_path)
                saved += 1
            except Exception as exc:
                failed += 1
                self._append_log(f"Save failed for {src}: {exc}")

        QMessageBox.information(
            self,
            "Save complete",
            f"Saved: {saved} files\\nFailed: {failed} files",
        )
        self._append_log(f"Save finished - saved={saved}, failed={failed}")
