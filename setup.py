from setuptools import setup

setup(
    name="latrivex-cli",
    version="1.0.0",
    py_modules=["latrivex_cli"],
    install_requires=[
        "typer[all]",
        "rich",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "latrivex = latrivex_cli:app",
        ],
    },
)