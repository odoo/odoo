import sys
import time
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

class VendAIDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VendAI - Smart POS")
        
        # Create web view widget
        self.browser = QWebEngineView()
        self.browser.page().loadFinished.connect(self.onLoadFinished)
        self.setCentralWidget(self.browser)
        
        # Set window size
        self.setGeometry(100, 100, 1280, 800)
        
        # Load Odoo web interface with retry mechanism
        self.retries = 0
        self.max_retries = 3
        self.loadOdoo()
    
    def loadOdoo(self):
        self.browser.setUrl(QUrl("http://localhost:8069"))
    
    def onLoadFinished(self, ok):
        if not ok and self.retries < self.max_retries:
            self.retries += 1
            print(f"Retry {self.retries} of {self.max_retries}...")
            QTimer.singleShot(2000, self.loadOdoo)
        elif not ok:
            QMessageBox.critical(self, "Error",
                "Could not connect to Odoo server.\nPlease make sure it's running on http://localhost:8069")
        else:
            self.retries = 0

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = VendAIDesktop()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error starting application: {e}")
