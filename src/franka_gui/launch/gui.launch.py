from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "gripper_action",
            default_value="/panda_hand_controller/gripper_cmd",
            description="GripperCommand action name.",
        ),
        DeclareLaunchArgument(
            "move_action",
            default_value="/move_action",
            description="MoveIt MoveGroup action name.",
        ),
        DeclareLaunchArgument(
            "joint_states_topic",
            default_value="/joint_states",
            description="JointState topic name.",
        ),
        DeclareLaunchArgument(
            "camera_topic",
            default_value="/detection_camera/image",
            description="Bridged Gazebo camera image topic.",
        ),
        DeclareLaunchArgument(
            "annotated_topic",
            default_value="/franka_sorting/annotated_image",
            description="Annotated detection image topic used when available.",
        ),
        Node(
            package="franka_gui",
            executable="franka_gui",
            name="franka_gui",
            output="screen",
            parameters=[{
                "gripper_action": LaunchConfiguration("gripper_action"),
                "move_action": LaunchConfiguration("move_action"),
                "joint_states_topic": LaunchConfiguration("joint_states_topic"),
                "camera_topic": LaunchConfiguration("camera_topic"),
                "annotated_topic": LaunchConfiguration("annotated_topic"),
            }],
        ),
    ])
