"""Shared constants for the Franka Panda control GUI."""

# Joint limits from franka_description/urdf/properties.xacro
ARM_JOINTS = [
    ("panda_joint1", -2.8973, 2.8973),
    ("panda_joint2", -1.7628, 1.7628),
    ("panda_joint3", -2.8973, 2.8973),
    ("panda_joint4", -3.0718, -0.0698),
    ("panda_joint5", -2.8973, 2.8973),
    ("panda_joint6", -0.0175, 3.7525),
    ("panda_joint7", -2.8973, 2.8973),
]

JOINT_NAMES = [name for name, _, _ in ARM_JOINTS]

FINGER_JOINT = "panda_finger_joint1"
GRIPPER_MIN, GRIPPER_MAX = 0.0, 0.05
GRIPPER_OPEN, GRIPPER_CLOSED = GRIPPER_MAX, 0.0

# ROS interfaces
MOVE_GROUP = "panda_arm"
MOVE_ACTION = "/move_action"
GRIPPER_ACTION = "/panda_hand_controller/gripper_cmd"
JOINT_STATES_TOPIC = "/joint_states"
CAMERA_TOPIC = "/detection_camera/image"
ANNOTATED_TOPIC = "/franka_sorting/annotated_image"

# Sorting interfaces
SORT_START_SERVICE = "/franka_sorting/start"
SORT_STOP_SERVICE = "/franka_sorting/stop"
SORT_STATUS_TOPIC = "/franka_sorting/status"
DETECTED_COUNT_TOPIC = "/franka_sorting/detected_count"
PLACED_COUNT_TOPIC = "/franka_sorting/placed_count"

# Frames
BASE_FRAME = "world"
TCP_LINK = "panda_hand_tcp"

# Motion defaults
VELOCITY_SCALE = 0.25
ACCELERATION_SCALE = 0.25
PLANNING_TIME = 5.0
PLANNING_ATTEMPTS = 5
JOINT_TOLERANCE = 0.01
POSITION_TOLERANCE = 0.01
ORIENTATION_TOLERANCE = 0.20

# Default end-effector target (world frame, above the table)
DEFAULT_XYZ = (0.55, 0.0, 0.80)
