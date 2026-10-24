from glob import glob
from setuptools import setup

package_name = 'franka_gui'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Ahmed Gaber',
    maintainer_email='ahmedmgaber28@gmail.com',
    description='PySide6 control GUI for the simulated Franka Panda.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'franka_gui = franka_gui.main:main',
        ],
    },
)
