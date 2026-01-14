"""
LAES - Liquid Air Energy Storage Model
======================================

A first-principles thermodynamic and economic model for LAES systems.

Installation:
    pip install -e .

Usage:
    python -m laes --help
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="laes",
    version="1.0.0",
    author="[Your Name]",
    author_email="your.email@example.com",
    description="Liquid Air Energy Storage thermodynamic and economic model",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/laes",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "CoolProp>=6.4.0",
        "numpy>=1.20.0",
        "matplotlib>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
    },
    entry_points={
        "console_scripts": [
            "laes=laes.cli:main",
        ],
    },
    keywords="energy storage, liquid air, LAES, thermodynamics, cryogenic",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/laes/issues",
        "Source": "https://github.com/yourusername/laes",
    },
)
