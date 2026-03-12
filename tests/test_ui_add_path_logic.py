import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication

from dicom_editor.ui import MainWindow


def test_add_uses_selected_tag_not_previous_path_tag():
    app = QApplication.instance() or QApplication([])
    w = MainWindow()

    # previous selected row path points to PatientName
    w.input_path.setCurrentText("00100010")
    w.input_tag.setCurrentText("Approval Status (300E,0002)")
    w.input_vr.setText("CS")
    w.input_value.setCurrentText("APPROVED")

    op = w._build_operation("add")
    assert op.tag == 0x300E0002
    assert op.path == "300E0002"

    w.close()


def test_add_defaults_to_root_even_if_selected_row_path_is_nested():
    app = QApplication.instance() or QApplication([])
    w = MainWindow()

    w.input_path.setCurrentText("00400275[0].00100010")
    w.input_tag.setCurrentText("Approval Status (300E,0002)")
    w.input_vr.setText("CS")
    w.input_value.setCurrentText("APPROVED")

    op = w._build_operation("add")
    assert op.tag == 0x300E0002
    assert op.path == "300E0002"

    w.close()


def test_add_keeps_explicit_path_when_final_tag_matches():
    app = QApplication.instance() or QApplication([])
    w = MainWindow()

    w.input_tag.setCurrentText("Approval Status (300E,0002)")
    w.input_path.setCurrentText("00400275[0].300E0002")
    w.input_vr.setText("CS")
    w.input_value.setCurrentText("APPROVED")

    op = w._build_operation("add")
    assert op.tag == 0x300E0002
    assert op.path == "00400275[0].300E0002"

    w.close()
