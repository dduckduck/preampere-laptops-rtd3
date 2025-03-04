#!/usr/bin/env python
from setuptools import setup

setup(
    name="rtd3",
    version="0.1.0",
    description="Utility to verify NVIDIA requirements for RTD3 and monitor the current dGPU state",
    author="Timur Sorokin",
    author_email="timursorokin94@gmail.com",
    url="https://github.com/dduckduck/preampere-laptops-rtd3/",
    keywords=["nvidia", "prime", "rtd3"],
    licence="GPL",
    py_modules=["rtd3"],
    entry_points={
        "console_scripts": [
            "rtd3=rtd3:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Linux",
    ],
    python_requires=">=3.7",
)
