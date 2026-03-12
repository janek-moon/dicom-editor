from PySide6.QtWidgets import QApplication

from dicom_editor.ui import MainWindow


def test_approval_status_value_options_include_presets_with_existing_value():
    app = QApplication.instance() or QApplication([])
    w = MainWindow()

    class R:
        def __init__(self, path, tag, name, value):
            self.path = path
            self.tag = tag
            self.name = name
            self.vr = "CS"
            self.value = value

    w.current_rows = [R("300E0002", "(300E,0002)", "Approval Status", "APPROVED")]
    w._refresh_value_select_for_tag("Approval Status (300E,0002)")
    items = [w.input_value.itemText(i) for i in range(w.input_value.count())]

    assert "APPROVED" in items
    assert "REJECTED" in items
    assert "UNAPPROVED" in items

    w.close()
