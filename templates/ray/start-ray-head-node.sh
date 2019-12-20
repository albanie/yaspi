#!/bin/bash

# This script is responsible for initialising the ray head node on whichever
# machine slurm has assigned to it

# Setup the environment for Ray
{{env_setup}}

# Launch the head node
ray start --head --redis-port=6379

# Prevent the slurm scheduler from releasing the machine
sleep infinity
echo "Ray head node was stopped"