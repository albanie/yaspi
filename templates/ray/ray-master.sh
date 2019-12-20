#!/bin/bash

# Generate a temporary text file to share state between the workers.  This must be
# somewhere on the home folder (i.e. not in $TMPDIR).  Its sole purpose is to pass the
# address of the head node to the worker nodes.
TMPDIR="${HOME}/tmp/ray-scripts"
mkdir -p "${TMPDIR}"
tmpfile=$(mktemp "${TMPDIR}/ray-scheduler.XXXXXX")
echo "created tmpfile at $tmpfile to share ray meta data"

# sleep to ensure the temporary file has time to propagate over NFS
sleep {{nfs_update_secs}}

# Launch the ray job
sbatch --export=all,tmpfile=$tmpfile {{ray_sbatch_path}}