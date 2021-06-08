"""
Yaspi setup.py

Build/upload commands:
coverage run -m pytest .
python3 setup.py sdist bdist_wheel
twine upload --skip-existing dist/*
"""
from pathlib import Path

import setuptools

with open("README.md", "r") as f:
    long_description = f.read()


# Ensure that extra data (example scripts and recipe templates) are included
package_dir = "yaspi"
extra_package_patterns = ["misc/*.py", "templates/**/*.sh"]
extra_package_files = []
for pattern in extra_package_patterns:
    paths = Path(package_dir).glob(pattern)
    rel_paths = [str(x.relative_to(package_dir)) for x in paths]
    extra_package_files.extend(rel_paths)


setuptools.setup(
    name="yaspi",
    version="0.0.4",
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
    package_dir={"yaspi": package_dir},
    package_data={"yaspi": extra_package_files},
    install_requires=[
        "watchlogs",
        "beartype"
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        'Operating System :: POSIX :: Linux',
    ],
)
