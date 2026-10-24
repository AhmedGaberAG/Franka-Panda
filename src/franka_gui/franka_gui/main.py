#!/usr/bin/env python3
"""Entry point for the Franka Panda control GUI."""

import os
import sys

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from franka_gui import DARK_STYLE, FrankaRosNode, MainWindow, RosBridge


def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)

    bridge = RosBridge()
    node = FrankaRosNode(bridge)
    window = MainWindow(node)
    window.show()

    executor = SingleThreadedExecutor()
    executor.add_node(node)

    spin_timer = QTimer(window)
    spin_timer.setInterval(5)

    def spin_once():
        if not rclpy.ok():
            spin_timer.stop()
            return
        try:
            executor.spin_once(timeout_sec=0.0)
        except (ExternalShutdownException, KeyboardInterrupt):
            spin_timer.stop()
        except Exception as exc:  # noqa: BLE001
            spin_timer.stop()
            if rclpy.ok():
                node.get_logger().error(f"ROS executor error: {exc}")

    spin_timer.timeout.connect(spin_once)
    spin_timer.start()

    def shutdown():
        spin_timer.stop()
        window.stop()
        executor.shutdown(timeout_sec=2.0)
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    app.aboutToQuit.connect(shutdown)
    exit_code = app.exec()

    # rclpy's action-client objects can double-free while the interpreter is
    # finalising after a goal was used.  ROS resources are already released
    # in shutdown(), so skip interpreter teardown instead of aborting.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)


if __name__ == "__main__":
    main()
