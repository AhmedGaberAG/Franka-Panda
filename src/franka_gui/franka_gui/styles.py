"""QSS styles for the Franka Panda control GUI."""

DARK_STYLE = """
QMainWindow, QWidget {
    background: #0a0f17;
    color: #e6edf7;
    font-family: 'Inter', 'DejaVu Sans';
    font-size: 10pt;
}

QFrame#Header {
    background: #0f1723;
    border: 1px solid #1d2a3d;
    border-radius: 14px;
}

QFrame#Panel {
    background: #0f1723;
    border: 1px solid #1d2a3d;
    border-radius: 14px;
}

QFrame#CameraFrame {
    background: #05080d;
    border: 1px solid #1d2a3d;
    border-radius: 10px;
}

QLabel#Title {
    font-size: 19pt;
    font-weight: 700;
    color: #f4f8ff;
}

QLabel#Subtitle {
    color: #7d91ab;
    font-size: 9pt;
}

QLabel#PanelTitle {
    color: #dbe7f7;
    font-size: 11pt;
    font-weight: 700;
}

QLabel#SectionTitle {
    color: #9fb4cf;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#Muted {
    color: #7d91ab;
    font-size: 9pt;
}

QLabel#Live {
    color: #6f86a3;
    font-size: 9pt;
}

QLabel#Target {
    color: #dce8f8;
    font-size: 9pt;
    font-weight: 700;
}

QLabel#Message {
    color: #8ea6c4;
    font-size: 9pt;
}

QLabel#CameraPlaceholder {
    color: #5d718c;
    font-size: 10pt;
}

QPushButton {
    background: #162233;
    border: 1px solid #273a53;
    border-radius: 8px;
    padding: 8px 12px;
    color: #dce8f8;
}
QPushButton:hover {
    background: #1c2d44;
    border-color: #3b82f6;
}
QPushButton:pressed {
    background: #12324f;
}
QPushButton:disabled {
    background: #101822;
    border-color: #1a2534;
    color: #4d5f76;
}

QPushButton#Primary {
    background: #1d6fe0;
    border: 1px solid #3b82f6;
    font-weight: 700;
    color: #ffffff;
}
QPushButton#Primary:hover {
    background: #2b7ff0;
}
QPushButton#Primary:pressed {
    background: #155cb8;
}

QPushButton#Ghost {
    background: transparent;
    border: 1px solid #2a3d56;
    color: #9db3ce;
}
QPushButton#Ghost:hover {
    background: #162233;
    border-color: #3b82f6;
}

QPushButton#Danger {
    background: #2a1620;
    border: 1px solid #5c2638;
    color: #f2a3b6;
}
QPushButton#Danger:hover {
    background: #381b28;
    border-color: #a03050;
}
QPushButton#Danger:disabled {
    background: #171015;
    border-color: #2a1a22;
    color: #634151;
}

QSlider::groove:horizontal {
    background: #1d2a3d;
    height: 6px;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #eaf2ff;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid #3b82f6;
}
QSlider::handle:horizontal:hover {
    background: #ffffff;
}
QSlider::handle:horizontal:disabled {
    background: #5d718c;
    border-color: #33465f;
}

QDoubleSpinBox {
    background: #0b1320;
    border: 1px solid #273a53;
    border-radius: 7px;
    padding: 6px 8px;
    selection-background-color: #1d6fe0;
}
QDoubleSpinBox:focus {
    border-color: #3b82f6;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: transparent;
    border: none;
    width: 16px;
}

QProgressBar {
    background: #101a28;
    border: 0;
    border-radius: 4px;
    height: 8px;
}
QProgressBar::chunk {
    background: #3b82f6;
    border-radius: 4px;
}

QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    border: none;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #273a53;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QToolTip {
    background: #162233;
    color: #e6edf7;
    border: 1px solid #273a53;
    border-radius: 6px;
    padding: 6px 10px;
}
"""
