import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # Package paths
    description_share = get_package_share_directory("franka_description")
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    # Launch arguments
    world_arg = DeclareLaunchArgument(
        "world_name",
        default_value="warehouse",
        description="World name; loads worlds/<world_name>.world.",
    )
    gui_arg = DeclareLaunchArgument(
        "use_gazebo_gui",
        default_value="true",
        description="Start Gazebo GUI",
    )
    sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
    )
    hand_arg = DeclareLaunchArgument("hand", default_value="true")
    self_collision_arg = DeclareLaunchArgument(
        "with_sc", default_value="false"
    )

    world_name = LaunchConfiguration("world_name")
    use_gazebo_gui = LaunchConfiguration("use_gazebo_gui")
    use_sim_time = LaunchConfiguration("use_sim_time")
    hand = LaunchConfiguration("hand")
    with_sc = LaunchConfiguration("with_sc")

    # Gazebo version settings
    ros_distro = os.environ.get("ROS_DISTRO", "humble")
    is_ignition = "True" if ros_distro == "humble" else "False"
    physics_engine = (
        ""
        if ros_distro == "humble"
        else "--physics-engine gz-physics-bullet-featherstone-plugin"
    )
    gz_version = {"humble": "6", "iron": "7", "jazzy": "8"}.get(
        ros_distro, "9"
    )

    # Robot description
    xacro_file = os.path.join(
        description_share, "urdf", "panda.urdf.xacro"
    )

    # The Panda is mounted on the table in worlds/warehouse.world.
    # Keep this height in sync with the table top and franka_moveit.
    table_height = "0.55"

    # Optional MoveIt-owned initial joint positions. When present, the
    # simulated hardware starts in the same state MoveIt uses.
    try:
        moveit_share = get_package_share_directory("franka_moveit")
        initial_positions_file = os.path.join(
            moveit_share, "config", "initial_positions.yaml"
        )
        if not os.path.isfile(initial_positions_file):
            initial_positions_file = ""
    except Exception:
        initial_positions_file = ""

    xacro_args = [
        " hand:=", hand,
        " with_sc:=", with_sc,
        " is_sim:=true",
        " is_ignition:=", is_ignition,
        " use_world:=true",
        " world_xyz:='0 0 ", table_height, "'",
    ]
    if initial_positions_file:
        xacro_args += [
            " initial_positions_file:=", initial_positions_file
        ]

    robot_description = ParameterValue(
        Command(["xacro ", xacro_file] + xacro_args),
        value_type=str,
    )

    # Gazebo resource paths
    resource_path = os.pathsep.join([
        str(Path(description_share).parent.resolve()),
        os.path.join(description_share, "models"),
    ])

    gazebo_resources = [
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
        SetEnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", resource_path),
    ]

    # Start Gazebo with the selected world
    world_file = PathJoinSubstitution([
        description_share,
        "worlds",
        [world_name, ".world"],
    ])

    gazebo_launch_file = os.path.join(
        ros_gz_sim_share, "launch", "gz_sim.launch.py"
    )

    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gazebo_launch_file),
        launch_arguments={
            "gz_args": [
                "-r -v 4 ",
                physics_engine,
                " ",
                world_file,
            ],
            "gz_version": gz_version,
        }.items(),
        condition=IfCondition(use_gazebo_gui),
    )

    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gazebo_launch_file),
        launch_arguments={
            "gz_args": [
                "-r -v 4 -s ",
                physics_engine,
                " ",
                world_file,
            ],
            "gz_version": gz_version,
        }.items(),
        condition=UnlessCondition(use_gazebo_gui),
    )

    # Publish robot TF and description
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": use_sim_time,
        }],
    )

    # Spawn Panda into Gazebo
    spawn_panda = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_panda",
        output="screen",
        arguments=[
            "-topic", "robot_description",
            "-name", "panda",
        ],
    )

    # Gazebo bridges: clock, conveyor poses, and pause command
    gazebo_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gazebo_bridge",
        output="screen",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            [
                "/world/",
                world_name,
                "/dynamic_pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            ],
            "/conveyor/pause@std_msgs/msg/Bool]gz.msgs.Boolean",
            "/detection_camera/image@sensor_msgs/msg/Image[gz.msgs.Image",
            "/detection_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
        ],
    )

    # Conveyor helper (from franka_utils)
    conveyor_control = Node(
        package="franka_utils",
        executable="conveyor_control.py",
        name="conveyor_control",
        output="screen",
        parameters=[{
            "pose_topic": [
                "/world/", world_name, "/dynamic_pose/info"
            ],
            # Stop the cube within the Panda's verified reach window.
            "target_x": 0.70,
            "use_sim_time": use_sim_time,
        }],
    )

    return LaunchDescription([
        world_arg,
        gui_arg,
        sim_time_arg,
        hand_arg,
        self_collision_arg,
        *gazebo_resources,
        gazebo_gui,
        gazebo_headless,
        robot_state_publisher,
        spawn_panda,
        gazebo_bridge,
        conveyor_control,
    ])
