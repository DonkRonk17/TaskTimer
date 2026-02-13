#!/usr/bin/env python3
"""Setup script for TaskTimer."""

from setuptools import setup
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="tasktimer",
    version="1.0.0",
    description="Pomodoro-style productivity timer with Team Brain integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ATLAS (Team Brain)",
    author_email="contact@metaphy.com",
    url="https://github.com/DonkRonk17/TaskTimer",
    py_modules=["tasktimer"],
    python_requires=">=3.7",
    install_requires=[
        # No external dependencies!
    ],
    entry_points={
        "console_scripts": [
            "tasktimer=tasktimer:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Utilities",
    ],
    keywords="pomodoro timer productivity focus time-tracking analytics",
)
