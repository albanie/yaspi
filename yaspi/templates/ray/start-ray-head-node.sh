#!/bin/bash

# This script is responsible for initialising the ray head node on whichever
# machine slurm has assigned to it

# Setup the environment for Ray
echo "setting up environment for ray head node"
{{env_setup}}

echo "starting ray head node"
# Launch the head node
ray start --head --redis-port=6379 --include-webui {{ray_args}}
echo "started ray head node"

# Prevent the slurm scheduler from releasing the machine
sleep infinity
echo "Ray head node was stopped"