"""A minimal working example for Ray usage with yaspi.

See the official documentation for examples and tutorials:
https://ray.readthedocs.io/en/latest/
"""
import ray
import time
import argparse
from datetime import datetime


@ray.remote
def remote_function():
    time.sleep(5)
    return datetime.now()


def main():
    parser = argparse.ArgumentParser(description="Minimal Ray example")
    parser.add_argument("--local_mode", action="store_true", help="run on local machine")
    parser.add_argument("--ray_address", help="address of the ray head node")
    args = parser.parse_args()

    # initialise the server
    ray.init(
        address=args.ray_address,
        local_mode=args.local_mode,
        ignore_reinit_error=1,
    )

    # execute functions
    timestamps = [remote_function.remote() for _ in range(4)]
    for worker_timestamp in timestamps:
        print(f"timestamp from worker: {ray.get(worker_timestamp)}")


if __name__ == "__main__":
    main()
