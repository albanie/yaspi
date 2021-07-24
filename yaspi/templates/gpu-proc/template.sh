#!/bin/bash
#SBATCH --job-name={{job_name}}
#SBATCH --mem={{mem|ordeleteline}}
#SBATCH --array={{array}}
#SBATCH --time={{time_limit|ordeleteline}}
#SBATCH --output={{log_path}}
#SBATCH --partition={{partition|ordeleteline}}
#SBATCH --cpus-per-task={{cpus_per_task|ordeleteline}}
{{sbatch_resources}}
{{exclude_nodes}}
{{custom_directives}}
{{sbatch_resources}}
# -------------------------------

# enable terminal stdout logging
echo "linking job logs to terminal"
echo "=================================================================="

{{env_setup}}

# Run the loop of runs for this task.
worker_id=$((SLURM_ARRAY_TASK_ID - 1))
echo "($HOSTNAME) This is SLURM task $SLURM_ARRAY_TASK_ID, worker id $worker_id"
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
