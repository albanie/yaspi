import setuptools


with open("README.md", "r") as f:
    long_description = f.read()


setuptools.setup(
    name="yaspi",
    version="0.0.0.1",
    entry_points={
        "console_scripts": [
            "yaspi=yaspi.yaspi:main",
        ],
    },
    author="Samuel Albanie",
    description="Yet Another Slurm Python Interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/albanie/yaspi",
    packages=["yaspi"],
    python_requires=">=3.7",
    install_requires=[
        "watchlogs",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        'Operating System :: POSIX :: Linux',
    ],
)
