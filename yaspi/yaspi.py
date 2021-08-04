"""YASPI - yet another python slurm interface.
"""

import re
import shutil
import argparse
import subprocess
from typing import List, Union
from pathlib import Path
from datetime import datetime
from itertools import zip_longest

from beartype import beartype
from beartype.cave import NoneTypeOr
from watchlogs.watchlogs import Watcher


class Yaspi:

    @beartype
    def __init__(
            self,
            job_name: str,
            cmd: str,
            prep: str,
            recipe: str,
            gen_script_dir: Union[Path, str],
            log_dir: Union[Path, str],
            partition: NoneTypeOr[str],
            job_array_size: int,
            cpus_per_task: NoneTypeOr[int],
            gpus_per_task: NoneTypeOr[int],
            refresh_logs: bool,
            exclude: str,
            use_custom_ray_tmp_dir: bool,
            ssh_forward: str,
            time_limit: NoneTypeOr[str],
            throttle_array: int,
            mem: str,
            constraint_str: NoneTypeOr[str],
            custom_directives: str = "",
            template_dir: Path = Path(__file__).parent / "templates",
            job_queue: NoneTypeOr[str] = None,
            env_setup: NoneTypeOr[str] = None,
            code_snapshot_dir: NoneTypeOr[Path, str] = None,
            code_snapshot_filter_patterns: List[str] = ["**/*.py", "symlinks"],
    ):
        self.cmd = cmd
        self.mem = mem
        self.prep = prep
        self.recipe = recipe
        self.exclude = exclude
        self.job_name = job_name
        self.partition = partition
        self.time_limit = time_limit
        self.env_setup = env_setup
        self.job_queue = job_queue
        self.ssh_forward = ssh_forward
        self.refresh_logs = refresh_logs
        self.template_dir = Path(template_dir)
        self.cpus_per_task = cpus_per_task
        self.gpus_per_task = gpus_per_task
        self.constraint_str = constraint_str
        self.throttle_array = throttle_array
        self.job_array_size = job_array_size
        self.use_custom_ray_tmp_dir = use_custom_ray_tmp_dir
        self.custom_directives = custom_directives
        self.gen_script_dir = Path(gen_script_dir)
        if code_snapshot_dir is not None:
            self.code_snapshot_dir = Path(code_snapshot_dir).resolve()
        else:
            self.code_snapshot_dir = None
        self.code_snapshot_filter_patterns = code_snapshot_filter_patterns
        self.slurm_logs = None
        # SLURM expects the logfiles to be absolute paths
        self.log_dir = Path(log_dir).resolve()
        self.generate_scripts()

    def generate_scripts(self):
        gen_dir = self.gen_script_dir
        if self.env_setup is None:
            self.env_setup = (
                'export PYTHONPATH="${BASE}":$PYTHONPATH\n'
                'export PATH="${HOME}/local/anaconda3/condabin/:$PATH"\n'
                'source ~/local/anaconda3/etc/profile.d/conda.sh\n'
                'conda activate pt37'
            )

        # set up logging
        ts = datetime.now().strftime(r"%Y-%m-%d_%H-%M-%S")
        self.log_path = str(Path(self.log_dir) / self.job_name / ts / "%4a-log.txt")

        if self.code_snapshot_dir is not None:
            supported_recipes = {"cpu-proc", "gpu-proc"}
            assert self.recipe in supported_recipes, (
                f"For now, `code_snapshot_dir` is only supported for {supported_recipes}"
                f" ({self.recipe} is not yet supported)"
            )
            code_snapshot_dir = self.code_snapshot_dir / self.job_name / ts
            self.copy_to_snapshot_dir(code_snapshot_dir=code_snapshot_dir)
            # modify the srun command to first move to the code snapshot directory before
            # the user command is launched
            self.cmd = f"cd {code_snapshot_dir} ; {self.cmd}"

        if self.recipe == "ray":
            # TODO(Samuel): configure this more sensibly
            template_paths = {
                "master": "ray/ray-master.sh",
                "sbatch": "ray/ray-sbatch.sh",
                "head-node": "ray/start-ray-head-node.sh",
                "worker-node": "ray/start-ray-worker-node.sh",
            }
            # NOTE: Due to unix max socket length (108 characters) it's best if this is
            # short and absolute
            if self.use_custom_ray_tmp_dir:
                ray_tmp_dir = Path.home() / "data/sock"
                ray_tmp_dir.mkdir(exist_ok=True, parents=True)
                ray_args = f"--temp-dir={ray_tmp_dir}"
            else:
                ray_args = ""
            array_str = f"1-{self.job_array_size}"
            if self.throttle_array:
                array_str = f"{array_str}%{self.throttle_array}"
            rules = {
                "master": {
                    "nfs_update_secs": 1,
                    "ray_sbatch_path": str(gen_dir / template_paths["sbatch"]),
                },
                "sbatch": {
                    "cmd": self.cmd,
                    "mem": self.mem,
                    "log_path": self.log_path,
                    "job_name": self.job_name,
                    "partition": self.partition,
                    "time_limit": self.time_limit,
                    "env_setup": self.env_setup,
                    "array": array_str,
                    "cpus_per_task": self.cpus_per_task,
                    "approx_ray_init_time_in_secs": 10,
                    "exclude_nodes": f"#SBATCH --exclude={self.exclude}",
                    "head_init_script": str(gen_dir / template_paths["head-node"]),
                    "worker_init_script": str(gen_dir / template_paths["worker-node"]),
                    "ssh_forward": self.ssh_forward,
                },
                "head-node": {
                    "ray_args": ray_args,
                    "env_setup": self.env_setup,
                },
                "worker-node": {
                    "ray_args": ray_args,
                    "env_setup": self.env_setup,
                },
            }
            self._add_batch_resources(rules)
        elif self.recipe in {"cpu-proc", "gpu-proc"}:
            if self.env_setup is None:
                # TODO(Samuel): configure this more sensibly
                self.env_setup = (
                    'export PYTHONPATH="${BASE}":$PYTHONPATH\n'
                    'export PATH="${HOME}/local/anaconda3/condabin/:$PATH"\n'
                    'source ~/local/anaconda3/etc/profile.d/conda.sh\n'
                    'conda activate pt14'
                )
            template_paths = {
                "master": f"{self.recipe}/master.sh",
                "sbatch": f"{self.recipe}/template.sh",
            }
            array_str = f"1-{self.job_array_size}"
            if self.throttle_array:
                array_str = f"{array_str}%{self.throttle_array}"
            rules = {
                "master": {
                    "sbatch_path": str(gen_dir / template_paths["sbatch"]),
                },
                "sbatch": {
                    "cmd": self.cmd,
                    "mem": self.mem,
                    "prep": self.prep,
                    "array": array_str,
                    "log_path": self.log_path,
                    "job_name": self.job_name,
                    "job_queue": self.job_queue,
                    "env_setup": self.env_setup,
                    "partition": self.partition,
                    "time_limit": self.time_limit,
                    "cpus_per_task": self.cpus_per_task,
                    "exclude_nodes": f"#SBATCH --exclude={self.exclude}",
                    "custom_directives": self.custom_directives,
                    "sbatch_resources": None,
                },
            }
            self._add_batch_resources(rules, self.recipe == "gpu-proc")
        else:
            raise ValueError(f"template: {self.recipe} unrecognised")

        template_paths = {key: Path(self.template_dir) / val
                          for key, val in template_paths.items()}

        self.gen_scripts = {}
        for key, template_path in template_paths.items():
            gen = self.fill_template(template_path=template_path, rules=rules[key])
            dest_path = gen_dir / Path(template_path).relative_to(self.template_dir)
            self.gen_scripts[key] = dest_path
            dest_path.parent.mkdir(exist_ok=True, parents=True)
            with open(str(dest_path), "w") as f:
                print(f"Writing slurm script ({key}) to {dest_path}")
                f.write(gen)
            dest_path.chmod(0o755)

    def _add_batch_resources(self, rules, allow_gpu=True):
        resource_strs = []
        if self.constraint_str:
            resource_strs.append(f"#SBATCH --constraint={self.constraint_str}")
        if self.gpus_per_task and allow_gpu:
            resource_strs.append(f"#SBATCH --gres=gpu:{self.gpus_per_task}")
        rules["sbatch"]["sbatch_resources"] = "\n".join(resource_strs)

    @beartype
    def copy_to_snapshot_dir(self, code_snapshot_dir: Path):
        src_files_to_copy = set()
        for pattern in self.code_snapshot_filter_patterns:
            if pattern == "symlinks":
                candidates = Path(".").glob("**/*")
                src_files = [x for x in candidates if x.is_symlink()]
            else:
                src_files = list(Path(".").glob(pattern))
            src_files_to_copy.update(src_files)

        print(f"Copying {len(src_files_to_copy)} src files to {code_snapshot_dir}")
        for src_file in src_files_to_copy:
            dest_path = code_snapshot_dir / src_file
            dest_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(str(src_file), str(dest_path), follow_symlinks=False)

    def get_log_paths(self):
        watched_logs = []
        for idx in range(self.job_array_size):
            if self.recipe == "ray" and idx > 0:
                # for ray jobs, we only need to watch the log from the headnode
                break
            slurm_id = idx + 1
            watched_log = Path(str(self.log_path).replace("%4a", f"{slurm_id:04d}"))
            watched_log.parent.mkdir(exist_ok=True, parents=True)
            if self.refresh_logs:
                if watched_log.exists():
                    watched_log.unlink()
                    # We also remove Pygtail files
                    pygtail_file = watched_log.with_suffix(".txt.offset")
                    if pygtail_file.exists():
                        pygtail_file.unlink()
            # We must make sure that the log file exists to enable monitoring
            if not watched_log.exists():
                print(f"Creating watch log: {watched_log} for the first time")
                watched_log.touch()
            watched_logs.append(str(watched_log.resolve()))
        return watched_logs

    @beartype
    def submit(self, watch: bool = True, conserve_resources: int = 5):
        if watch:
            watched_logs = self.get_log_paths()
        submission_cmd = f"bash {self.gen_scripts['master']}"
        print(f"Submitting job with command: {submission_cmd}")
        print(f"using command:\n{self.cmd}")
        out = subprocess.check_output(submission_cmd.split())
        job_id = out.decode("utf-8").rstrip()

        def halting_condition():
            job_state = f"scontrol show job {job_id}"
            out = subprocess.check_output(job_state.split())
            regex = "JobState=[A-Z]+"
            completed = True
            for match in re.finditer(regex, out.decode("utf-8").rstrip()):
                status = match.group().replace("JobState=", "")
                if status != "COMPLETED":
                    return False
            return completed

        if watch:
            Watcher(
                heartbeat=True,
                watched_logs=watched_logs,
                halting_condition=halting_condition,
                conserve_resources=conserve_resources,
            ).run()
            print("Job completed")

    def __repr__(self):
        """Produce a human-readable string representation of the Yaspi object.

        Returns:
            (str): a summary of the object settings.
        """
        summary = "Yaspi object\n========================\n"
        kwargs = sorted(self.__dict__.items(), key=lambda x: len(str(x[0]) + str(x[1])))
        for key, val in kwargs:
            summary += f"{key}: {val}\n"
        return summary

    @beartype
    def fill_template(self, template_path: Path, rules: dict) -> str:
        """Transform a template according to a given set of rules.

        Args:
            template_path: location of the template to be filled.
            rules (dict[str:object]): a key, value mapping between template keys
                and their target values.

        Returns:
            A single string represnting the transformed contents of the template
                file.
        """
        generated = []
        with open(template_path, "r") as f:
            template = f.read().splitlines()

        # A template key use to denote sbatch directives that can be removed
        # if no value is specified
        OR_DELETE_LINE = "|ordeleteline"

        for row in template:
            skip_row = False
            edits = []
            regex = r"\{\{(.*?)\}\}"
            for match in re.finditer(regex, row):
                groups = match.groups()
                assert len(groups) == 1, "expected single group"
                key = groups[0]
                ordeleteline = False
                if key.endswith(OR_DELETE_LINE):
                    ordeleteline = True
                    key = key[:-len(OR_DELETE_LINE)]
                token = rules[key]
                if ordeleteline and token is None:
                    skip_row = True
                    break
                edits.append((match.span(), token))
            if skip_row:
                continue
            if edits:
                # invert the spans
                spans = [(None, 0)] + [x[0] for x in edits] + [(len(row), None)]
                inverse_spans = [(x[1], y[0]) for x, y in zip(spans, spans[1:])]
                tokens = [row[start:stop] for start, stop in inverse_spans]
                urls = [str(x[1]) for x in edits]
                new_row = ""
                for token, url in zip_longest(tokens, urls, fillvalue=""):
                    new_row += token + url
                row = new_row
            generated.append(row)
        return "\n".join(generated)


def main():
    parser = argparse.ArgumentParser(description="Yaspi Tool")
    parser.add_argument("--install_location", action="store_true",
                        help="if given, report the install location of yaspi")
    parser.add_argument("--job_name", default="yaspi-test",
                        help="the name that slurm will give to the job")
    parser.add_argument("--recipe", default="ray",
                        help="the SLURM recipe to use to generate scripts")
    parser.add_argument("--template_dir",
                        type=Path,
                        help="if given, override directory containing SLURM templates")
    parser.add_argument("--partition", default=None,
                        help="The name of the SLURM partition used to run the job")
    parser.add_argument("--time_limit", default=None,
                        help="The maximum amount of time allowed to run the job")
    parser.add_argument("--gen_script_dir", default="data/slurm-gen-scripts",
                        type=Path,
                        help="directory in which generated slurm scripts will be stored")
    parser.add_argument("--cmd", default='echo "hello"',
                        help="single command (or comma separated commands) to run")
    parser.add_argument("--mem", default=None,
                        help="the memory to be requested for each SLURM worker")
    parser.add_argument("--prep", default="", help="a command to be run before srun")
    parser.add_argument("--job_array_size", type=int, default=2,
                        help="The number of SLURM array workers")
    parser.add_argument("--cpus_per_task", type=int, default=None,
                        help="the number of cpus requested for each SLURM task")
    parser.add_argument("--gpus_per_task", type=int, default=None,
                        help="the number of gpus requested for each SLURM task")
    parser.add_argument("--throttle_array", type=int, default=0,
                        help="limit the number of array workers running at once")
    parser.add_argument("--env_setup", help="setup string for a custom environment")
    parser.add_argument("--ssh_forward",
                        default="ssh -N -f -R 8080:localhost:8080 triton.robots.ox.ac.uk",
                        help="setup string for a custom environment")
    parser.add_argument("--log_dir", default="data/slurm-logs", type=str,
                        help="location where SLURM logs will be stored")
    parser.add_argument("--use_custom_ray_tmp_dir", action="store_true")
    parser.add_argument("--refresh_logs", action="store_true")
    parser.add_argument("--watch", type=int, default=1,
                        help="whether to watch the generated SLURM logs")
    parser.add_argument("--exclude", default="",
                        help="comma separated list of nodes to exclude")
    parser.add_argument("--constraint_str", help="SLURM --constraint string")
    parser.add_argument("--job_queue", default="",
                        help="a queue of jobs to pass to a yaspi recipe")
    parser.add_argument("--custom_directives", default="",
                        help=('Add any extra directives here, separated by newlines'
                              'e.g. "#SBATCH -A account-name\n#SBATCH --mem 10G"'))
    parser.add_argument("--code_snapshot_dir", type=Path,
                        help=("if this argument is supplied, yaspi will make a snapshot "
                              "of the codebase (starting from the current root directory),"
                              "copy the snapshot to `code_snapshot_dir`, and then launch"
                              "the command from there. Currently, only supported for the"
                              "'cpu-proc' and 'gpu-proc' recipes"))
    parser.add_argument("--code_snapshot_filter_patterns", nargs="+",
                        default=["**/*.py", "symlinks"],
                        help=("if `--code_snapshot_dir` is supplied, then "
                              "`--code_snapshot_filter_patterns` is used as a glob pattern "
                              "to select which files will be included in the snapshot.  If "
                              "`symlinks` is included as a filter pattern, it is treated "
                              "as a special pattern that mimics symlinks in the original "
                              "code dir"))
    args = parser.parse_args()

    if args.install_location:
        print(Path(__file__).parent)
        return

    # Certain properties use defaults set by the Yaspi class, rather than argparse, to
    # ensure that users of the Python interface (i.e. directly creating Yaspi object)
    # can aslo benefit from these defaults
    prop_keys = {"template_dir", "custom_directives"}
    prop_kwargs = {key: getattr(args, key) for key in prop_keys if getattr(args, key)}

    job = Yaspi(
        cmd=args.cmd,
        mem=args.mem,
        prep=args.prep,
        recipe=args.recipe,
        log_dir=args.log_dir,
        exclude=args.exclude,
        job_name=args.job_name,
        job_queue=args.job_queue,
        partition=args.partition,
        time_limit=args.time_limit,
        env_setup=args.env_setup,
        ssh_forward=args.ssh_forward,
        refresh_logs=args.refresh_logs,
        cpus_per_task=args.cpus_per_task,
        gpus_per_task=args.gpus_per_task,
        gen_script_dir=args.gen_script_dir,
        constraint_str=args.constraint_str,
        job_array_size=args.job_array_size,
        use_custom_ray_tmp_dir=args.use_custom_ray_tmp_dir,
        throttle_array=args.throttle_array,
        code_snapshot_dir=args.code_snapshot_dir,
        code_snapshot_filter_patterns=args.code_snapshot_filter_patterns,
        **prop_kwargs,
    )
    job.submit(watch=bool(args.watch))


if __name__ == "__main__":
    main()
