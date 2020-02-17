#!/bin/bash
#SBATCH --job-name={{job_name}}
#SBATCH --mem={{mem}}
#SBATCH --array={{array}}
#SBATCH --time={{time_limit}}
#SBATCH --output={{log_path}}
#SBATCH --partition={{partition}}
#SBATCH --cpus-per-task={{cpus_per_task}}
{{sbatch_resources}}
{{exclude_nodes}}
# -------------------------------

# enable terminal stdout logging
echo "linking job logs to terminal"
echo "=================================================================="

{{env_setup}}

# Run the loop of runs for this task.
worker_id=$((SLURM_ARRAY_TASK_ID - 1))
echo "This is SLURM task $SLURM_ARRAY_TASK_ID, worker id $worker_id"
declare -a custom_args_queue=({{job_queue}})

# handle potential ipython issues with history
export IPYTHONDIR=/tmp

prep="{{prep}}"
echo "running prep cmd $prep"
eval "${prep}" 

cmd="{{cmd}}"
cmd="srun --unbuffered ${cmd} ${custom_args_queue[${worker_id}]}"
echo "running cmd $cmd"
eval "${cmd}" 