import os
import sys
import subprocess
from pathlib import Path
from . import rootify, ensure_shebang

def in_slurm():
    return "SLURM_JOB_ID" in os.environ

def reroot():
    path_to_script = Path(sys.argv[0]).resolve()
    ensure_shebang(path_to_script)
    return path_to_script

def simple(**kwargs):
    path_to_script = reroot()
    if in_slurm():
        return
    args = [
        "sbatch",
        # parameters:
        *(
            arg for half in (
                ("--" + key.replace("_", "-"), value) for key, value in kwargs.items()
            ) for arg in half
        ),
        "--",
        path_to_script,
    ]
    process = subprocess.run(args)

def multi(iterable, **kwargs):
    path_to_script = reroot()
    if in_slurm():
        for i, conf in enumerate(iterable):
            if i == int(os.environ["SLURM_ARRAY_TASK_ID"]):
                return conf
    iter_length = sum(1 for _ in iterable)
    process = subprocess.run([
        "sbatch",
        # parameters:
        *(
            arg for half in (
                ("--" + key.replace("_", "-"), value) for key, value in kwargs.items()
            ) for arg in half
        ),
        "--array=0-" + str(iter_length - 1),
        "--",
        path_to_script,
    ])
