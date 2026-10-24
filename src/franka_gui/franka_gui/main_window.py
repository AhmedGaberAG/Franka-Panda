"""Two-panel main window for the Franka Panda GUI."""

import time

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .constants import (
    ARM_JOINTS, CAMERA_TOPIC, DEFAULT_XYZ, FINGER_JOINT, GRIPPER_CLOSED,
    GRIPPER_MAX, GRIPPER_OPEN,
)
from .widgets import CameraView, JointRow, StatusChip


class MainWindow(QMainWindow):
    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node
        self.bridge = node.bridge
        self._move_buttons = []

        self.setWindowTitle("Franka Panda Control")
        self.resize(1180, 760)
        self.setMinimumSize(1000, 660)

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(100)

        self._moveit_ok = False
        self._moveit_checked = 0.0
        self._message_text = None
        self._counts = None
        self._sort_status_text = None
        self._gripper_text = None

    # ------------------------------------------------------------------ UI setup
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        outer.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_camera_panel(), 3)
        body.addWidget(self._build_controls_panel(), 2)
        outer.addLayout(body, 1)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(78)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Franka Panda")
        title.setObjectName("Title")
        subtitle = QLabel("ROS 2 · MoveIt 2 · Gazebo")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        layout.addStretch()

        self.chip_camera = StatusChip("Camera")
        self.chip_robot = StatusChip("Robot")
        self.chip_moveit = StatusChip("MoveIt")
        self.chip_motion = StatusChip("Motion")
        self.chip_sorting = StatusChip("Sorting")
        for chip in (self.chip_camera, self.chip_robot,
                     self.chip_moveit, self.chip_motion,
                     self.chip_sorting):
            layout.addWidget(chip)

        return header

    def _build_camera_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("Live Camera · Detection")
        title.setObjectName("PanelTitle")
        topic = QLabel(CAMERA_TOPIC)
        topic.setObjectName("Muted")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(topic)
        layout.addLayout(title_row)

        frame = QFrame()
        frame.setObjectName("CameraFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(6, 6, 6, 6)
        self.camera_view = CameraView("Waiting for camera stream…")
        frame_layout.addWidget(self.camera_view)
        layout.addWidget(frame, 1)

        self.camera_footer = QLabel(
            "Gazebo detection camera · 0 cubes detected · 0 placed")
        self.camera_footer.setObjectName("Muted")
        layout.addWidget(self.camera_footer)

        return panel

    def _build_controls_panel(self):
        panel = QFrame()
        panel.setObjectName("Panel")

        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        scroll.setWidget(content)

        # Joint control -----------------------------------------------------
        layout.addLayout(self._section_title("JOINT CONTROL"))
        header = QGridLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setHorizontalSpacing(10)
        h_joint = QLabel("JOINT")
        h_live = QLabel("LIVE")
        h_target = QLabel("TARGET")
        for label in (h_joint, h_live, h_target):
            label.setObjectName("SectionTitle")
        h_live.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h_target.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(h_joint, 0, 0)
        header.addWidget(h_live, 0, 2)
        header.addWidget(h_target, 0, 3)
        header.setColumnStretch(1, 1)
        layout.addLayout(header)

        self.joint_rows = []
        for index, (name, low, high) in enumerate(ARM_JOINTS):
            row = JointRow(index, name, low, high)
            self.joint_rows.append(row)
            layout.addWidget(row)

        joint_buttons = QHBoxLayout()
        joint_buttons.setSpacing(8)
        sync = self._button("Sync from Robot", "Ghost")
        sync.clicked.connect(self._sync_joints)
        move_joints = self._button("Move Joints", "Primary")
        move_joints.clicked.connect(self._move_joints)
        joint_buttons.addWidget(sync)
        joint_buttons.addWidget(move_joints, 1)
        layout.addLayout(joint_buttons)
        self._move_buttons.append(move_joints)

        layout.addWidget(self._divider())

        # End effector ------------------------------------------------------
        layout.addLayout(self._section_title("END EFFECTOR · WORLD FRAME"))
        xyz_row = QHBoxLayout()
        xyz_row.setSpacing(8)
        self.xyz_spins = []
        for axis, value in zip("XYZ", DEFAULT_XYZ):
            spin = QDoubleSpinBox()
            spin.setRange(-2.0, 2.0)
            spin.setDecimals(3)
            spin.setSingleStep(0.01)
            spin.setValue(value)
            spin.setPrefix(f"{axis}  ")
            spin.setToolTip(f"Target {axis} in the world frame (m)")
            self.xyz_spins.append(spin)
            xyz_row.addWidget(spin)
        layout.addLayout(xyz_row)

        ee_buttons = QHBoxLayout()
        ee_buttons.setSpacing(8)
        use_current = self._button("Use Current", "Ghost")
        use_current.clicked.connect(self._use_current_tcp)
        move_ee = self._button("Move End Effector", "Primary")
        move_ee.clicked.connect(self._move_end_effector)
        ee_buttons.addWidget(use_current)
        ee_buttons.addWidget(move_ee, 1)
        layout.addLayout(ee_buttons)
        self._move_buttons.append(move_ee)

        layout.addWidget(self._divider())

        # Gripper -----------------------------------------------------------
        layout.addLayout(self._section_title("GRIPPER"))
        grip_live_row = QHBoxLayout()
        self.gripper_bar = QProgressBar()
        self.gripper_bar.setRange(0, round(GRIPPER_MAX * 1000))
        self.gripper_bar.setTextVisible(False)
        self.gripper_bar.setFixedHeight(8)
        self.gripper_live = QLabel("—")
        self.gripper_live.setObjectName("Live")
        self.gripper_live.setFixedWidth(58)
        self.gripper_live.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grip_live_row.addWidget(self.gripper_bar, 1)
        grip_live_row.addWidget(self.gripper_live)
        layout.addLayout(grip_live_row)

        grip_buttons = QHBoxLayout()
        grip_buttons.setSpacing(8)
        open_btn = self._button("Open", "Ghost")
        open_btn.clicked.connect(lambda: self.node.set_gripper(GRIPPER_OPEN))
        close_btn = self._button("Close", "Ghost")
        close_btn.clicked.connect(lambda: self.node.set_gripper(GRIPPER_CLOSED))
        grip_buttons.addWidget(open_btn)
        grip_buttons.addWidget(close_btn)
        layout.addLayout(grip_buttons)

        layout.addWidget(self._divider())

        # Sorting -----------------------------------------------------------
        layout.addLayout(self._section_title("SORTING"))
        counts_row = QHBoxLayout()
        counts_row.setSpacing(12)
        self.detected_label = QLabel("Cubes detected: 0")
        self.detected_label.setObjectName("Live")
        self.placed_label = QLabel("Placed: 0")
        self.placed_label.setObjectName("Live")
        counts_row.addWidget(self.detected_label)
        counts_row.addStretch()
        counts_row.addWidget(self.placed_label)
        layout.addLayout(counts_row)

        sort_buttons = QHBoxLayout()
        sort_buttons.setSpacing(8)
        start_sort = self._button(
            "Start Sorting", "Primary",
            "Detect cubes and place them into the matching colour bins")
        start_sort.clicked.connect(self.node.start_sorting)
        stop_sort = self._button(
            "Stop Sorting", "Danger",
            "Cancel the active sorting motion and keep the robot stationary")
        stop_sort.clicked.connect(self.node.stop_sorting)
        sort_buttons.addWidget(start_sort, 1)
        sort_buttons.addWidget(stop_sort)
        layout.addLayout(sort_buttons)

        self.sort_status = QLabel("Sorting idle.")
        self.sort_status.setObjectName("Message")
        self.sort_status.setWordWrap(True)
        self.sort_status.setMinimumHeight(34)
        layout.addWidget(self.sort_status)

        layout.addWidget(self._divider())

        # Motion safety -----------------------------------------------------
        self.cancel_button = self._button(
            "Cancel Motion", "Danger",
            "Cancels the active MoveIt goal (no hardware E-stop available)")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.node.cancel_motion)
        layout.addWidget(self.cancel_button)

        self.message = QLabel("Ready.")
        self.message.setObjectName("Message")
        self.message.setWordWrap(True)
        self.message.setMinimumHeight(34)
        layout.addWidget(self.message)
        layout.addStretch()

        return panel

    def _section_title(self, text):
        row = QHBoxLayout()
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        row.addWidget(label)
        row.addStretch()
        return row

    def _divider(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background:#1d2a3d; border:none;")
        return line

    def _button(self, text, style, tooltip=None):
        button = QPushButton(text)
        button.setObjectName(style)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(34)
        if tooltip:
            button.setToolTip(tooltip)
        return button

    # ------------------------------------------------------------------ updates
    @Slot()
    def on_image(self):
        image = self.node.take_image()
        if image is not None:
            self.camera_view.set_image(image)

    @Slot(str, bool)
    def on_motion(self, text, busy):
        disabled = busy
        for button in self._move_buttons:
            button.setEnabled(not disabled)
        self.cancel_button.setEnabled(busy)

        if busy:
            self.chip_motion.set_status("busy", text)
        elif text.lower().startswith("failed"):
            self.chip_motion.set_status("error", text)
        else:
            self.chip_motion.set_status("ok", text)

    @Slot(str)
    def on_message(self, text):
        if text == self._message_text:
            return
        self._message_text = text
        self.message.setText(text)

    @Slot(int, int)
    def on_sort_counts(self, detected, placed):
        counts = (detected, placed)
        if counts == self._counts:
            return
        self._counts = counts
        self.detected_label.setText(f"Cubes detected: {detected}")
        self.placed_label.setText(f"Placed: {placed}")
        self.camera_footer.setText(
            f"Gazebo detection camera · {detected} cubes detected · "
            f"{placed} placed")

    @Slot(str)
    def on_sorting_status(self, text):
        if text == self._sort_status_text:
            return
        self._sort_status_text = text
        self.sort_status.setText(text)
        lowered = text.lower()
        if "failed" in lowered or "cancelled" in lowered:
            self.chip_sorting.set_status("error", "error")
        elif text.startswith("[idle]"):
            self.chip_sorting.set_status("ok", "idle")
        else:
            self.chip_sorting.set_status("busy", "running")

    # ------------------------------------------------------------------- slots
    def _sync_joints(self):
        positions = self.node.latest_positions
        count = 0
        for row, (name, _, _) in zip(self.joint_rows, ARM_JOINTS):
            if name in positions:
                row.set_target(positions[name])
                count += 1
        self.on_message(
            f"Synced {count}/{len(ARM_JOINTS)} joints from /joint_states."
            if count else "No joint states received yet.")

    def _move_joints(self):
        self.node.move_joints([row.value() for row in self.joint_rows])

    def _use_current_tcp(self):
        pose = self.node.current_tcp()
        if pose is None:
            self.on_message("Current TCP unavailable (TF not ready).")
            return
        (x, y, z), _ = pose
        for spin, value in zip(self.xyz_spins, (x, y, z)):
            spin.setValue(value)
        self.on_message(f"Current TCP: X={x:.3f}  Y={y:.3f}  Z={z:.3f} m")

    def _move_end_effector(self):
        x, y, z = (spin.value() for spin in self.xyz_spins)
        self.node.move_xyz(x, y, z)

    # ------------------------------------------------------------------ refresh
    def _refresh(self):
        self.on_image()

        value = self.bridge.motion.take()
        if value is not None:
            self.on_motion(*value)
        value = self.bridge.message.take()
        if value is not None:
            self.on_message(value)
        value = self.bridge.sort_counts.take()
        if value is not None:
            self.on_sort_counts(*value)
        value = self.bridge.sorting_status.take()
        if value is not None:
            self.on_sorting_status(value)

        positions = self.node.latest_positions

        for row, (name, _, _) in zip(self.joint_rows, ARM_JOINTS):
            row.set_live(positions.get(name))

        finger = positions.get(FINGER_JOINT)
        if finger is None:
            millimetres = None
            text = "—"
        else:
            millimetres = max(0, min(round(GRIPPER_MAX * 1000),
                                     round(finger * 1000)))
            text = f"{millimetres} mm"
        if text != self._gripper_text:
            self._gripper_text = text
            if millimetres is not None:
                self.gripper_bar.setValue(millimetres)
            self.gripper_live.setText(text)

        camera_ok = self.node.camera_ok()
        self.chip_camera.set_status(
            "ok" if camera_ok else "off", "live" if camera_ok else "no signal")
        self.chip_robot.set_status("ok" if self.node.joints_ok() else "off")

        now = time.monotonic()
        if now - self._moveit_checked > 2.0:
            self._moveit_checked = now
            self._moveit_ok = self.node.moveit_ready()
        self.chip_moveit.set_status("ok" if self._moveit_ok else "off")

    def stop(self):
        self._timer.stop()
