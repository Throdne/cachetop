#!/usr/bin/env python3
"""
Setup script for cachetop - Real-time LVM cache monitor
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read version from script
def get_version():
    version = "1.0.0"  # Default version
    return version

setup(
    name="cachetop",
    version=get_version(),
    author="LVM Cache Monitor",
    author_email="",
    description="Real-time LVM cache monitoring tool similar to htop",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/cachetop",
    py_modules=["cachetop"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
    install_requires=[
        # No external dependencies - uses only standard library
    ],
    entry_points={
        "console_scripts": [
            "cachetop=cachetop:main",
        ],
    },
    keywords="lvm cache monitoring htop system administration storage",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/cachetop/issues",
        "Source": "https://github.com/yourusername/cachetop",
        "Documentation": "https://github.com/yourusername/cachetop#readme",
    },
)
