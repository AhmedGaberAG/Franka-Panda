"""
ROS 2 backend for the Franka Panda GUI.

ROS callbacks update thread-safe state; the GUI reads that state on its timer.
"""

import math
import threading
import time

from geometry_msgs.msg import Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints, JointConstraint, MotionPlanRequest, OrientationConstraint,
    PositionConstraint,
)
from PySide6.QtGui import QImage
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Image, JointState
from shape_msgs.msg import SolidPrimitive
from action_msgs.msg import GoalStatus
from control_msgs.action import GripperCommand
from std_msgs.msg import Int32, String
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener

from .constants import (
    ACCELERATION_SCALE, ANNOTATED_TOPIC, ARM_JOINTS, BASE_FRAME,
    CAMERA_TOPIC, DETECTED_COUNT_TOPIC, FINGER_JOINT, GRIPPER_ACTION,
    GRIPPER_MAX, GRIPPER_MIN, JOINT_STATES_TOPIC, JOINT_TOLERANCE,
    MOVE_ACTION, MOVE_GROUP, ORIENTATION_TOLERANCE, PLACED_COUNT_TOPIC,
    PLANNING_ATTEMPTS, PLANNING_TIME, POSITION_TOLERANCE, SORT_START_SERVICE,
    SORT_STATUS_TOPIC, SORT_STOP_SERVICE, TCP_LINK, VELOCITY_SCALE,
)


class _Event:
    """Small thread-safe mailbox used instead of cross-thread Qt signals."""

    def __init__(self):
        self._lock = threading.Lock()
        self._value = None

    def emit(self, *args):
        value = args[0] if len(args) == 1 else args
        with self._lock:
            self._value = value

    def take(self):
        with self._lock:
            value = self._value
            self._value = None
        return value


class RosBridge:
    """Thread-safe state shared by the ROS executor and the GUI thread."""

    def __init__(self):
        self.motion = _Event()   # (status text, busy)
        self.message = _Event()  # last event / diagnostic message
        self.sort_counts = _Event()   # (detected, placed)
        self.sorting_status = _Event()


_IMAGE_FORMATS = {
    "rgb8": QImage.Format_RGB888,
    "bgr8": QImage.Format_BGR888,
    "rgba8": QImage.Format_RGBA8888,
    "bgra8": QImage.Format_ARGB32,
    "mono8": QImage.Format_Grayscale8,
}


def _image_to_buffer(msg: Image):
    """Copy a sensor_msgs/Image into a transportable buffer."""
    fmt = _IMAGE_FORMATS.get(msg.encoding)
    if fmt is None:
        return None
    if msg.step <= 0 or msg.width <= 0 or msg.height <= 0:
        return None
    return bytes(msg.data), msg.width, msg.height, msg.step, fmt


def _buffer_to_qimage(buffer):
    data, width, height, step, fmt = buffer
    image = QImage(data, width, height, step, fmt)
    return image.copy()


class FrankaRosNode(Node):
    """ROS interface only; it never touches Qt widgets directly."""

    def __init__(self, bridge: RosBridge):
        super().__init__("franka_gui")
        self.bridge = bridge

        self.declare_parameter("gripper_action", GRIPPER_ACTION)
        self.declare_parameter("move_action", MOVE_ACTION)
        self.declare_parameter("joint_states_topic", JOINT_STATES_TOPIC)
        self.declare_parameter("camera_topic", CAMERA_TOPIC)
        self.declare_parameter("annotated_topic", ANNOTATED_TOPIC)
        self.declare_parameter("sort_start_service", SORT_START_SERVICE)
        self.declare_parameter("sort_stop_service", SORT_STOP_SERVICE)
        self.declare_parameter("sort_status_topic", SORT_STATUS_TOPIC)
        self.declare_parameter("detected_count_topic", DETECTED_COUNT_TOPIC)
        self.declare_parameter("placed_count_topic", PLACED_COUNT_TOPIC)

        gripper_action = self.get_parameter("gripper_action").value
        move_action = self.get_parameter("move_action").value
        joint_topic = self.get_parameter("joint_states_topic").value
        camera_topic = self.get_parameter("camera_topic").value
        annotated_topic = self.get_parameter("annotated_topic").value
        self._sort_start_service = self.get_parameter(
            "sort_start_service").value
        self._sort_stop_service = self.get_parameter(
            "sort_stop_service").value
        sort_status_topic = self.get_parameter("sort_status_topic").value
        detected_topic = self.get_parameter("detected_count_topic").value
        placed_topic = self.get_parameter("placed_count_topic").value

        self._gripper_client = ActionClient(self, GripperCommand, gripper_action)
        self._move_client = ActionClient(self, MoveGroup, move_action)
        self._sort_start_client = self.create_client(
            Trigger, self._sort_start_service)
        self._sort_stop_client = self.create_client(
            Trigger, self._sort_stop_service)

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self.latest_positions = {}
        self.last_joint_time = 0.0
        self.last_image_time = 0.0
        self._move_handle = None
        self._move_active = False
        self._first_joint = True
        self._first_image = True
        self._first_annotated = True
        self._raw_image = None
        self._annotated_image = None
        self._annotated_time = 0.0
        self._image_lock = threading.Lock()
        self._latest_image = None
        self.detected_count = 0
        self.placed_count = 0

        self.create_subscription(JointState, joint_topic, self._on_joint_state, 10)
        self.create_subscription(
            Image, camera_topic, self._on_image, qos_profile_sensor_data)
        self.create_subscription(
            Image, annotated_topic, self._on_annotated_image,
            qos_profile_sensor_data)
        self.create_subscription(
            String, sort_status_topic, self._on_sorting_status, 10)
        self.create_subscription(
            Int32, detected_topic, self._on_detected_count, 10)
        self.create_subscription(
            Int32, placed_topic, self._on_placed_count, 10)

        self.get_logger().info(
            f"GUI backend ready. MoveIt: {move_action}, gripper: {gripper_action}, "
            f"camera: {camera_topic}, annotated: {annotated_topic}")

    # ------------------------------------------------------------------ status
    def joints_ok(self):
        return time.monotonic() - self.last_joint_time < 1.0

    def camera_ok(self):
        return time.monotonic() - self.last_image_time < 2.0

    def moveit_ready(self):
        try:
            return self._move_client.server_is_ready()
        except Exception:  # noqa: BLE001 - context may already be shutting down
            return False

    def gripper_ready(self):
        try:
            return self._gripper_client.server_is_ready()
        except Exception:  # noqa: BLE001
            return False

    # ---------------------------------------------------------------- callbacks
    def _on_joint_state(self, msg):
        self.latest_positions = dict(zip(msg.name, msg.position))
        self.last_joint_time = time.monotonic()
        if self._first_joint:
            self._first_joint = False
            self.bridge.message.emit("/joint_states connected")

    def _on_image(self, msg):
        image = _image_to_buffer(msg)
        if image is None:
            return
        self.last_image_time = time.monotonic()
        self._raw_image = image
        if self._first_image:
            self._first_image = False
            self.get_logger().info(
                f"Camera stream: {msg.width}x{msg.height} {msg.encoding}")
        if time.monotonic() - self._annotated_time > 1.0:
            self._publish_image(image)

    def _on_annotated_image(self, msg):
        image = _image_to_buffer(msg)
        if image is None:
            return
        self._annotated_image = image
        self._annotated_time = time.monotonic()
        if self._first_annotated:
            self._first_annotated = False
            self.get_logger().info(
                f"Detection stream: {msg.width}x{msg.height} {msg.encoding}")
        self._publish_image(image)

    def _publish_image(self, image):
        with self._image_lock:
            self._latest_image = image

    def take_image(self):
        with self._image_lock:
            buffer = self._latest_image
            self._latest_image = None
        if buffer is None:
            return None
        return _buffer_to_qimage(buffer)

    def _on_sorting_status(self, msg):
        self.bridge.sorting_status.emit(msg.data)

    def _on_detected_count(self, msg):
        self.detected_count = int(msg.data)
        self.bridge.sort_counts.emit(
            self.detected_count, self.placed_count)

    def _on_placed_count(self, msg):
        self.placed_count = int(msg.data)
        self.bridge.sort_counts.emit(
            self.detected_count, self.placed_count)

    # --------------------------------------------------------------- robot pose
    def current_tcp(self):
        """Latest TCP pose (position + quaternion) in BASE_FRAME, or None."""
        try:
            tf = self._tf_buffer.lookup_transform(BASE_FRAME, TCP_LINK, Time())
        except Exception as exc:  # noqa: BLE001 - TF error types vary
            self.get_logger().debug(f"TCP lookup failed: {exc}")
            return None
        t = tf.transform.translation
        q = tf.transform.rotation
        return (t.x, t.y, t.z), (q.w, q.x, q.y, q.z)

    # ------------------------------------------------------------------ motion
    def _validate_joints(self, positions):
        if len(positions) != len(ARM_JOINTS):
            self.bridge.message.emit(
                f"Expected {len(ARM_JOINTS)} joint values, got {len(positions)}.")
            return False
        for value, (name, low, high) in zip(positions, ARM_JOINTS):
            if not math.isfinite(value) or not low <= value <= high:
                self.bridge.message.emit(
                    f"{name}={value:.3f} is outside [{low:.3f}, {high:.3f}] rad.")
                return False
        return True

    def _send_move_goal(self, constraints):
        if self._move_active:
            self.bridge.message.emit("A motion is already in progress.")
            return
        if not self._move_client.server_is_ready():
            self.bridge.message.emit(f"MoveIt action unavailable: {MOVE_ACTION}")
            return

        request = MotionPlanRequest()
        request.group_name = MOVE_GROUP
        request.num_planning_attempts = PLANNING_ATTEMPTS
        request.allowed_planning_time = PLANNING_TIME
        request.max_velocity_scaling_factor = VELOCITY_SCALE
        request.max_acceleration_scaling_factor = ACCELERATION_SCALE
        request.goal_constraints = [constraints]

        goal = MoveGroup.Goal()
        goal.request = request
        goal.planning_options.plan_only = False
        goal.planning_options.look_around = False
        goal.planning_options.replan = False

        self._move_active = True
        self.bridge.motion.emit("Planning…", True)
        self.bridge.message.emit("Sending MoveIt goal…")
        self._move_client.send_goal_async(
            goal,
            feedback_callback=self._on_move_feedback,
        ).add_done_callback(self._on_move_response)

    def move_joints(self, positions):
        if not self._validate_joints(positions):
            return
        constraints = Constraints()
        for (name, _, _), value in zip(ARM_JOINTS, positions):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = float(value)
            jc.tolerance_above = JOINT_TOLERANCE
            jc.tolerance_below = JOINT_TOLERANCE
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
        self._send_move_goal(constraints)

    def move_xyz(self, x, y, z):
        if not all(math.isfinite(v) for v in (x, y, z)):
            self.bridge.message.emit("XYZ target must be finite.")
            return

        constraints = Constraints()

        pc = PositionConstraint()
        pc.header.frame_id = BASE_FRAME
        pc.link_name = TCP_LINK
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [POSITION_TOLERANCE]
        pc.constraint_region.primitives.append(sphere)
        pose = Pose()
        pose.position.x = float(x)
        pose.position.y = float(y)
        pose.position.z = float(z)
        pc.constraint_region.primitive_poses.append(pose)
        pc.weight = 1.0
        constraints.position_constraints.append(pc)

        # Keep the current end-effector orientation when TF is available.
        current = self.current_tcp()
        if current is not None:
            _, (qw, qx, qy, qz) = current
            oc = OrientationConstraint()
            oc.header.frame_id = BASE_FRAME
            oc.link_name = TCP_LINK
            oc.orientation.w = qw
            oc.orientation.x = qx
            oc.orientation.y = qy
            oc.orientation.z = qz
            oc.absolute_x_axis_tolerance = ORIENTATION_TOLERANCE
            oc.absolute_y_axis_tolerance = ORIENTATION_TOLERANCE
            oc.absolute_z_axis_tolerance = ORIENTATION_TOLERANCE
            oc.weight = 1.0
            constraints.orientation_constraints.append(oc)
        else:
            self.bridge.message.emit(
                "Current orientation unavailable; planning position only.")

        self._send_move_goal(constraints)

    def _on_move_response(self, future):
        try:
            handle = future.result()
        except Exception as exc:  # noqa: BLE001
            self._finish_motion(f"Goal error: {exc}", False)
            return

        if not handle.accepted:
            self._finish_motion("MoveIt goal rejected.", False)
            return

        self._move_handle = handle
        handle.get_result_async().add_done_callback(self._on_move_result)

    def _on_move_feedback(self, feedback_msg):
        state = getattr(feedback_msg.feedback, "state", "") or ""
        labels = {
            "PLANNING": "Planning…",
            "MONITOR": "Moving…",
            "LOOK": "Looking for solution…",
        }
        label = labels.get(state.upper(), state.title() or "Moving…")
        self.bridge.motion.emit(label, True)

    def _on_move_result(self, future):
        try:
            wrapped = future.result()
            code = wrapped.result.error_code.val
            success = code == 1
        except Exception as exc:  # noqa: BLE001
            self._finish_motion(f"Result error: {exc}", False)
            return
        if wrapped.status == GoalStatus.STATUS_CANCELED:
            self._finish_motion("Idle", True, "Motion cancelled.")
        elif success:
            self._finish_motion("Idle", True, "Motion completed.")
        else:
            self._finish_motion(f"Failed (code {code})", False,
                                f"MoveIt failed with error code {code}.")

    def _finish_motion(self, status, ok, message=None):
        self._move_active = False
        self._move_handle = None
        self.bridge.motion.emit(status, False)
        if message:
            self.bridge.message.emit(message)

    def start_sorting(self):
        self._call_trigger(self._sort_start_client, "Sorting start")

    def stop_sorting(self):
        self._call_trigger(self._sort_stop_client, "Sorting stop")

    def _call_trigger(self, client, label):
        if not client.service_is_ready():
            self.bridge.message.emit(f"{label} service unavailable.")
            return
        future = client.call_async(Trigger.Request())
        future.add_done_callback(
            lambda result: self._on_trigger_result(result, label))

    def _on_trigger_result(self, future, label):
        try:
            result = future.result()
        except Exception as exc:  # noqa: BLE001
            self.bridge.message.emit(f"{label} error: {exc}")
            return
        state = "ok" if result.success else "failed"
        self.bridge.message.emit(f"{label} {state}: {result.message}")

    def cancel_motion(self):
        if self._move_handle is None:
            self.bridge.message.emit("No active motion to cancel.")
            return
        self._move_handle.cancel_goal_async()
        self.bridge.motion.emit("Cancelling…", True)
        self.bridge.message.emit("Cancellation requested.")

    # ----------------------------------------------------------------- gripper
    def set_gripper(self, position):
        position = float(position)
        if not GRIPPER_MIN <= position <= GRIPPER_MAX:
            self.bridge.message.emit(
                f"Gripper target must be in [{GRIPPER_MIN}, {GRIPPER_MAX}] m.")
            return
        if not self._gripper_client.server_is_ready():
            self.bridge.message.emit(f"Gripper action unavailable: {GRIPPER_ACTION}")
            return

        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = 10.0
        self.bridge.message.emit(
            f"Gripper → {position * 1000:.0f} mm ({'opening' if position > 0 else 'closing'}).")
        self._gripper_client.send_goal_async(
            goal).add_done_callback(self._on_gripper_response)

    def _on_gripper_response(self, future):
        try:
            handle = future.result()
        except Exception as exc:  # noqa: BLE001
            self.bridge.message.emit(f"Gripper goal error: {exc}")
            return
        if not handle.accepted:
            self.bridge.message.emit("Gripper goal rejected.")
            return
        handle.get_result_async().add_done_callback(self._on_gripper_result)

    def _on_gripper_result(self, future):
        try:
            result = future.result().result
        except Exception as exc:  # noqa: BLE001
            self.bridge.message.emit(f"Gripper result error: {exc}")
            return
        if result.reached_goal:
            self.bridge.message.emit(
                f"Gripper reached {result.position * 1000:.0f} mm.")
        elif result.stalled:
            self.bridge.message.emit("Gripper stalled (object detected).")
        else:
            self.bridge.message.emit(
                f"Gripper stopped at {result.position * 1000:.0f} mm.")

    # ------------------------------------------------------------------ helper
    def finger_position(self):
        return self.latest_positions.get(FINGER_JOINT)

    def shutdown(self):
        """
        Release the TF listener before the node is destroyed.

        tf2_ros.TransformListener.__del__ calls destroy_subscription(), which
        crashes if the owning node was already destroyed.  Unregister it once
        here (after the executor has stopped) and neutralise the destructor.
        """
        listener = getattr(self, "_tf_listener", None)
        if listener is None:
            return
        try:
            listener.unregister()
        except Exception:  # noqa: BLE001
            pass
        finally:
            listener.unregister = lambda: None
            self._tf_listener = None
