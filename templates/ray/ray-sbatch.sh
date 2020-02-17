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

# This script is a modification to the implementation suggest by gregSchwartz18 here:
# https://github.com/ray-project/ray/issues/826#issuecomment-522116599

worker_id=$((SLURM_ARRAY_TASK_ID - 1))
echo "($HOSTNAME) This is SLURM job: $SLURM_ARRAY_JOB_ID, worker id $worker_id"

# define a length of time (in seconds) for workers to wait while either the head node
# (or other workers) initiailise ray servers
approx_ray_init_time_in_secs={{approx_ray_init_time_in_secs}}

# The first array worker is responsible for managing the head-node.  All remaining array
# members will be used as ray workers.
if [ $worker_id -eq 0 ]; then

    # find the ip address of the machine that will be the head node and write it to disk
    # so that the other workers can connect to it
    ip_prefix=$(srun --ntasks=1 hostname --ip-address)
    echo "ip_prefix: ${ip_prefix}"

    # We will run the head node on the standard Redis port - we also write this
    # information to disk so that it can be accessed by the workers
    suffix=':6379'
    ip_head=$ip_prefix$suffix
    echo "Writing values to ${tmpfile}"
    echo $ip_head >> $tmpfile

    # run the head-node initialisation script
    head_init_script={{head_init_script}}
    srun -u --export=ALL --ntasks=1 "${head_init_script}" &
    echo "launched ${head_init_script}"
else
    # For each non-head worker, we first sleep to allow the head worker to write its
    # details to disk
    sleep ${approx_ray_init_time_in_secs}

    echo "====================================================="
    echo "running ray worker ${worker_id}"
    echo "====================================================="
    echo "reading head node information from: ${tmpfile}"
    readarray -t head_node_config < ${tmpfile}
    ip_head=${head_node_config[0]}
    echo "attaching to head node ip_head: ${ip_head}"

    worker_init_script={{worker_init_script}}
    srun -u --export=ALL --ntasks=1 ${worker_init_script} $ip_head $worker_id
    echo "launched ${cmd}"
fi

if [ $worker_id -eq 0 ]; then
    {{env_setup}}
    {{ssh_forward}}
    cmd="{{cmd}}"
    echo "Launching ${cmd} on head node in ${approx_ray_init_time_in_secs} secs"
    sleep ${approx_ray_init_time_in_secs}
    {{cmd}} --ray_address $ip_head
    echo "cancelling $SLURM_JOB_ID"
    scancel $SLURM_ARRAY_JOB_ID
fi
