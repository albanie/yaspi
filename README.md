### yaspi - yet another slurm python interface

The goal of `yaspi` is to provide an interface to submitting [slurm](https://slurm.schedmd.com/documentation.html) jobs, thereby obviating the joys of sbatch files.  It does so through `recipes` - these are collections of templates and rules for generating sbatch scripts.

It should be considered (highly) experimental. 

### Notes and Usage

The following command will launch a slurm job, with the name "example", that: (1) initialises a ray head node and a set of `$JOB_ARRAY_SIZE - 1` ray workers via a SLURM array job; (2) launches `$CMD` from the head node.

```
JOB_ARRAY_SIZE=2
CPUS_PER_TASK=5
GPUS_PER_TASK=1
CMD="echo 'hello there'"
python yaspi.py --job_name=example \
                --cmd="$CMD" \
                --job_array_size=${JOB_ARRAY_SIZE} \
                --cpus_per_task=${CPUS_PER_TASK} \
                --gpus_per_task=${GPUS_PER_TASK} \
                --recipe=cpu-proc \
                --refresh_logs
```


### Supported recipes:

* `cpu-proc` - a generic recipe for submitting CPU jobs via a job array.
* `gpu-proc` - a generic recipe for submitting GPU jobs via a job array.
* `ray` - job submissions for the [ray scheduler](https://github.com/ray-project/ray).


### Requirements:

`yaspi` has been tested on CentOS Linux release 7.7.1908 with slurm 18.08.7. YMMV on other platforms.