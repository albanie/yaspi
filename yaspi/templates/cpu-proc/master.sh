#!/bin/bash

# Launch the sbatch job
job_id=$(sbatch --parsable {{sbatch_path}})
echo $job_id