import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    description_share = get_package_share_directory("franka_description")
    controller_share = get_package_share_directory("franka_controller")
    moveit_share = get_package_share_directory("franka_moveit")

    # Launch arguments
    world_name_arg = DeclareLaunchArgument(
        "world_name",
        default_value="warehouse",
        description="Gazebo world name; loads worlds/<world_name>.world.",
    )
    gui_arg = DeclareLaunchArgument(
        "use_gazebo_gui",
        default_value="true",
        description="Start Gazebo GUI",
    )
    rviz_arg = DeclareLaunchArgument(
        "rviz",
        default_value="true",
        description="Start MoveIt RViz",
    )
    hand_arg = DeclareLaunchArgument("hand", default_value="true")
    with_sc_arg = DeclareLaunchArgument("with_sc", default_value="false")
    sim_time_arg = DeclareLaunchArgument("use_sim_time", default_value="true")
    start_sorting_arg = DeclareLaunchArgument(
        "start_sorting",
        default_value="true",
        description="Launch the franka_sorting node together with bringup.",
    )
    gui_arg_launch = DeclareLaunchArgument(
        "start_gui",
        default_value="true",
        description="Launch the franka_gui PySide6 GUI.",
    )
    sorting_config_arg = DeclareLaunchArgument(
        "sorting_config",
        default_value=PathJoinSubstitution([
            FindPackageShare("franka_sorting"),
            "config",
            "sorting.yaml",
        ]),
        description="Path to the sorting YAML configuration.",
    )

    world_name = LaunchConfiguration("world_name")
    use_gazebo_gui = LaunchConfiguration("use_gazebo_gui")
    rviz = LaunchConfiguration("rviz")
    hand = LaunchConfiguration("hand")
    with_sc = LaunchConfiguration("with_sc")
    use_sim_time = LaunchConfiguration("use_sim_time")
    start_sorting = LaunchConfiguration("start_sorting")
    start_gui = LaunchConfiguration("start_gui")
    sorting_config = LaunchConfiguration("sorting_config")

    # Gazebo simulation
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                description_share, "launch", "gazebo.launch.py"
            )
        ),
        launch_arguments={
            "world_name": world_name,
            "use_gazebo_gui": use_gazebo_gui,
            "use_sim_time": use_sim_time,
            "hand": hand,
            "with_sc": with_sc,
        }.items(),
    )

    # Robot controllers
    controllers = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                controller_share, "launch", "controller.launch.py"
            )
        ),
        launch_arguments={
            "hand": hand,
        }.items(),
    )

    # MoveIt and RViz
    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                moveit_share, "launch", "moveit.launch.py"
            )
        ),
        launch_arguments={
            "rviz": rviz,
            "hand": hand,
            "use_sim_time": use_sim_time,
        }.items(),
    )

    sorting = Node(
        package="franka_sorting",
        executable="sorting_node",
        name="franka_sorting",
        output="screen",
        condition=IfCondition(start_sorting),
        parameters=[{
            "config_path": sorting_config,
            "use_sim_time": use_sim_time,
        }],
    )

    gui = Node(
        package="franka_gui",
        executable="franka_gui",
        name="franka_gui",
        output="screen",
        condition=IfCondition(start_gui),
    )

    return LaunchDescription([
        world_name_arg,
        gui_arg,
        rviz_arg,
        hand_arg,
        with_sc_arg,
        sim_time_arg,
        start_sorting_arg,
        gui_arg_launch,
        sorting_config_arg,
        gazebo,
        controllers,
        moveit,
        sorting,
        gui,
    ])
