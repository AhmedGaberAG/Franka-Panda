import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    moveit_share = get_package_share_directory("franka_moveit")
    description_share = get_package_share_directory("franka_description")

    # Launch arguments
    rviz_arg = DeclareLaunchArgument(
        "rviz",
        default_value="true",
        description="Start RViz",
    )
    hand_arg = DeclareLaunchArgument(
        "hand",
        default_value="true",
        description="Enable the Franka hand",
    )
    prefix_arg = DeclareLaunchArgument(
        "prefix",
        default_value="",
        description="Robot link prefix",
    )
    sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation time",
    )

    rviz = LaunchConfiguration("rviz")
    hand = LaunchConfiguration("hand")
    prefix = LaunchConfiguration("prefix")
    use_sim_time = LaunchConfiguration("use_sim_time")

    # Build MoveIt configuration
    moveit_config = (
        MoveItConfigsBuilder(
            "panda",
            package_name="franka_moveit",
        )
        .robot_description(
            file_path=os.path.join(
                description_share,
                "urdf",
                "panda.urdf.xacro",
            ),
            mappings={
                "hand": hand,
                "prefix": prefix,
                "with_sc": "false",
                "is_sim": "false",
                "use_world": "true",
                # Must match the table height in franka_description
                # (worlds/warehouse.world + launch/gazebo.launch.py).
                "world_xyz": "0 0 0.55",
                # Canonical initial joint positions for the arm.
                "initial_positions_file": os.path.join(
                    moveit_share, "config", "initial_positions.yaml"
                ),
            },
        )
        .robot_description_semantic(
            file_path=os.path.join(moveit_share, "config", "panda.srdf")
        )
        .robot_description_kinematics(
            file_path=os.path.join(moveit_share, "config", "kinematics.yaml")
        )
        .joint_limits(
            file_path=os.path.join(moveit_share, "config", "joint_limits.yaml")
        )
        .trajectory_execution(
            file_path=os.path.join(
                moveit_share, "config", "moveit_controllers.yaml"
            )
        )
        .planning_pipelines(
            pipelines=["ompl"],
            default_planning_pipeline="ompl",
        )
        .to_moveit_configs()
    )

    moveit_parameters = {
        **moveit_config.to_dict(),
        "use_sim_time": use_sim_time,
        "moveit_manage_controllers": False,
        "trajectory_execution": {
            # The simulated system can run well below real time when the
            # camera and physics are active. Keep MoveIt from cancelling a
            # valid feedback-controlled trajectory just because Gazebo is slow.
            "allowed_execution_duration_scaling": 6.0,
            "allowed_goal_duration_margin": 5.0,
            "allowed_start_tolerance": 0.05,
        },
    }

    # MoveIt planning and execution
    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        # Let MoveIt choose its own node names. Forcing __node:=move_group
        # also renames its internal companion node and creates duplicate
        # /move_group entries in the ROS graph.
        output="screen",
        parameters=[moveit_parameters],
        arguments=["--ros-args", "--log-level", "info"],
    )

    # RViz
    rviz_config = os.path.join(
        moveit_share,
        "config",
        "moveit.rviz",
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        condition=IfCondition(rviz),
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            {"use_sim_time": use_sim_time},
        ],
    )

    return LaunchDescription([
        rviz_arg,
        hand_arg,
        prefix_arg,
        sim_time_arg,
        move_group,
        rviz_node,
    ])
