"""Minimal tests to validate syntax.

It would be possible to CI test SLURM launches by adding docker + slurmd to the
github workflow, but github doesn't give me enough free testing minutes for that :)
As a work around, tests that involve slurm submissions are only run for known
hostnames.
"""

import json
import socket
from pathlib import Path
from yaspi.yaspi import Yaspi


PATH_ARGS = {"gen_script_dir", "log_dir", "template_dir"}
HOSTS_WITH_SLURM = ["login1.triton.cluster"]


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
    if socket.gethostname() in HOSTS_WITH_SLURM:
        yaspi.submit()


def test_yaspi_object_creation_with_code_snapshot_dir():
    with open("yaspi_test/misc/dummy_yaspi_config.json", "r") as f:
        yaspi_defaults = json.load(f)
    for key, val in yaspi_defaults.items():
        if key in PATH_ARGS:
            yaspi_defaults[key] = Path(val)
    cmd = "python yaspi_test/misc/hello_world.py"
    yaspi_defaults["code_snapshot_dir"] = Path("data/code_snapshot_dir")
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
    if socket.gethostname() in HOSTS_WITH_SLURM:
        yaspi.submit()


def test_yaspi_object_line_deletion():
    with open("yaspi_test/misc/dummy_yaspi_config.json", "r") as f:
        yaspi_defaults = json.load(f)
    for key, val in yaspi_defaults.items():
        if key in PATH_ARGS:
            yaspi_defaults[key] = Path(val)
    cmd = "python yaspi_test/misc/hello_world.py"
    job_name = "test_yaspi"
    job_queue = ""

    # Check that yaspi only includes sbatch directives for values that
    # are not None when OR_DELETE_LINE is specified in the sbatch template.
    # This test uses the "constraint_str" flag as an example of a directive
    # that should be None by default

    # First, check that supplying a yaspi key-value pair ensures it is present
    yaspi_defaults["constraint_str"] = "p40"
    sbatch_directive = "#SBATCH --constraint"
    yaspi = Yaspi(
        cmd=cmd,
        job_name=job_name,
        job_queue=job_queue,
        job_array_size=1,
        **yaspi_defaults,
    )
    # Read the template that was written to disk
    with open("data/slurm-gen-scripts/cpu-proc/template.sh", "r") as f:
        template_contents = f.read()
    assert sbatch_directive in template_contents, (
        f"Expected to find {sbatch_directive} in template contents"
    )

    # Check that supplying a None-valued yaspi key-value pair ensures it is not present
    yaspi_defaults["constraint_str"] = None
    yaspi = Yaspi(
        cmd=cmd,
        job_name=job_name,
        job_queue=job_queue,
        job_array_size=1,
        **yaspi_defaults,
    )
    # Read the template that was written to disk
    with open("data/slurm-gen-scripts/cpu-proc/template.sh", "r") as f:
        template_contents = f.read()
    assert sbatch_directive not in template_contents, (
        f"Expected not to find {sbatch_directive} in template contents"
    )
    if socket.gethostname() in HOSTS_WITH_SLURM:
        yaspi.submit()


if __name__ == "__main__":
    test_yaspi_object_creation()
    test_yaspi_object_line_deletion()
    test_yaspi_object_creation_with_code_snapshot_dir()
