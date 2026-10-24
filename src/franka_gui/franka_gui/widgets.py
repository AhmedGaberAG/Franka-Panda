"""Reusable Qt widgets for the Franka Panda control GUI."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QSlider, QWidget
)

STATUS_COLORS = {
    "ok": "#22c55e",
    "off": "#64748b",
    "warn": "#f59e0b",
    "busy": "#3b82f6",
    "error": "#ef4444",
}


class JointRow(QWidget):
    """Joint name, target slider, live position and target position."""

    targetChanged = Signal(int, float)

    def __init__(self, index, name, low, high, parent=None):
        super().__init__(parent)
        self.index = index
        self.joint_name = name
        self.low = low
        self.high = high
        self._live_text = "—"

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)

        self.name_label = QLabel(name.replace("panda_joint", "J"))
        self.name_label.setObjectName("PanelTitle")
        self.name_label.setFixedWidth(26)
        self.name_label.setToolTip(
            f"{name}\nLimits: {low:+.3f} … {high:+.3f} rad")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(round(low * 1000), round(high * 1000))
        self.slider.setValue(round(max(low, min(high, 0.0)) * 1000))
        self.slider.setToolTip(f"Target: {0.0:+.3f} rad")

        self.live_label = QLabel("—")
        self.live_label.setObjectName("Live")
        self.live_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.live_label.setFixedWidth(62)

        self.target_label = QLabel(f"{0.0:+.3f}")
        self.target_label.setObjectName("Target")
        self.target_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.target_label.setFixedWidth(62)
        self.target_label.setToolTip("Target position (rad)")

        layout.addWidget(self.name_label, 0, 0)
        layout.addWidget(self.slider, 0, 1)
        layout.addWidget(self.live_label, 0, 2)
        layout.addWidget(self.target_label, 0, 3)
        layout.setColumnStretch(1, 1)

        self.slider.valueChanged.connect(self._on_value)

    def _on_value(self, value):
        target = value / 1000.0
        self.target_label.setText(f"{target:+.3f}")
        self.slider.setToolTip(f"Target: {target:+.3f} rad")
        self.targetChanged.emit(self.index, target)

    def set_target(self, value):
        clamped = max(self.low, min(self.high, float(value)))
        self.slider.setValue(round(clamped * 1000))

    def set_live(self, value):
        text = "—" if value is None else f"{float(value):+.2f}"
        if text == self._live_text:
            return
        self._live_text = text
        self.live_label.setText(text)

    def value(self):
        return self.slider.value() / 1000.0


class StatusChip(QWidget):
    """Small labelled status indicator with a coloured dot."""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._label_text = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.dot = QLabel("\u25cf")
        self.dot.setFixedWidth(12)
        self.text = QLabel(text)
        self.text.setObjectName("Muted")

        layout.addWidget(self.dot)
        layout.addWidget(self.text)

        self._status_key = None
        self.set_status("off")

    def set_status(self, state, extra=None):
        label = self._label_text if extra is None else f"{self._label_text}: {extra}"
        key = (state, label)
        if key == self._status_key:
            return
        self._status_key = key
        color = STATUS_COLORS.get(state, STATUS_COLORS["off"])
        self.dot.setStyleSheet(f"color:{color}; font-size:13px;")
        self.text.setText(label)


class CameraView(QLabel):
    """Aspect-ratio preserving image view with a placeholder message."""

    def __init__(self, placeholder, parent=None):
        super().__init__(parent)
        self._image = None
        self._placeholder = placeholder
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(480, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setObjectName("CameraPlaceholder")
        self.setText(placeholder)

    def set_image(self, image: QImage):
        self._image = image
        self._render()

    def clear_image(self):
        self._image = None
        self.setPixmap(QPixmap())
        self.setText(self._placeholder)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()

    def _render(self):
        if self._image is None or self._image.isNull():
            return
        pixmap = QPixmap.fromImage(self._image).scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pixmap)
