"""
Minimal tests to validate syntax.

It would be possible to CI test SLURM launches by adding docker + slurmd to the
github workflow, but github doesn't give me enough free testing minutes for that :)
"""

import json
from pathlib import Path
from yaspi.yaspi import Yaspi


PATH_ARGS = {"gen_script_dir", "log_dir", "template_dir"}


def test_yaspi_object_creation():
    with open("yaspi_test/misc/dummy_yaspi_config.json", "r") as f:
        yaspi_defaults = json.load(f)
    for key, val in yaspi_defaults.items():
        if key in PATH_ARGS:
            yaspi_defaults[key] = Path(val)
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
