"""
Minimal tests to validate syntax.

It would be possible to CI test SLURM launches by adding docker + slurmd to the
github workflow, but github doesn't give me enough free testing minutes for that :)
"""

from pathlib import Path
import json
from yaspi.yaspi import Yaspi


def test_yaspi_object_creation():
    with open("yaspi_test/misc/dummy_yaspi_config.json", "r") as f:
        yaspi_defaults = json.load(f)
    cmd = "python yaspi_test/misc/hello_world.py"
    job_name = "test_yaspi"
    job_queue = ""
    yaspi = Yaspi(
        cmd=cmd,
        job_name=job_name,
        job_queue=job_queue,
        job_array_size=1,
        **yaspi_defaults,
    )
    print(f"Test yaspi object: {yaspi}")


if __name__ == "__main__":
    test_yaspi_object_creation()