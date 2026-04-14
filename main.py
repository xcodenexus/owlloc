import sys
import os

# Qt WebEngine must be imported BEFORE QApplication is created
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-sandbox")

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from ui.styles import get_stylesheet
from ui.main_window import MainWindow
from core.device_manager import check_prerequisites


def main():
    # Required before QApplication when using QWebEngineView
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("OwlLoc")
    app.setApplicationDisplayName("OwlLoc — iOS Location Spoofer")
    app.setStyleSheet(get_stylesheet())

    # Prerequisites check
    issues = check_prerequisites()
    if issues:
        msg = QMessageBox()
        msg.setWindowTitle("OwlLoc — Setup Required")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Some requirements are missing:")
        msg.setDetailedText("\n\n".join(issues))
        msg.setInformativeText(
            "The app will still launch, but device detection may not work "
            "until these are resolved."
        )
        msg.exec()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
