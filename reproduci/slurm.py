import os
import sys
import itertools
import subprocess
from pathlib import Path

import click

from . import ensure_shebang

SCHEDULE_COMMAND = "sbatch"


def in_slurm():
    return "SLURM_JOB_ID" in os.environ


def reroot():
    path_to_script = Path(sys.argv[0]).resolve()
    ensure_shebang(path_to_script)
    return path_to_script


def _build_args(kwargs):
    yield from (
        str(arg)
        for half in (
            ("--" + key.replace("_", "-"), value) for key, value in kwargs.items()
        )
        for arg in half
    )


def simple(**kwargs):
    path_to_script = reroot()
    if in_slurm():
        return
    args = [
        SCHEDULE_COMMAND,
        # parameters:
        *_build_args(kwargs),
        "--",
        path_to_script,
    ]
    subprocess.run(args)
    raise SystemExit(0)


def multi(iterable, **kwargs):
    path_to_script = reroot()
    if in_slurm():
        for i, conf in enumerate(iterable):
            if i == int(os.environ["SLURM_ARRAY_TASK_ID"]):
                return conf
    iter_length = sum(1 for _ in iterable)
    subprocess.run(
        [
            SCHEDULE_COMMAND,
            # parameters:
            *_build_args(kwargs),
            "--array=0-" + str(iter_length - 1),
            "--",
            path_to_script,
        ]
    )
    raise SystemExit(0)


def Choice(*args, **kwargs):
    choice = click.Choice(*args, **kwargs)
    choice._reproduci_is_slurm_param = True
    return choice


class SlurmCommand(click.Command):
    def __init__(self, *args, slurm, **kwargs):
        super().__init__(*args, **kwargs)
        self.slurm_args = _build_args(slurm)
        self.slurm_configurations = self._get_slurm_configurations()
        self.slurm_schedule = None
        if not in_slurm():
            self.slurm_schedule = self.schedule()
        else:
            self.assign_defaults()

    def assign_defaults(self):
        for i, assignments in enumerate(self.slurm_configurations):
            if i == int(os.environ["SLURM_ARRAY_TASK_ID"]):
                for option, value in assignments:
                    option.default = value
                return

    def _get_slurm_configurations(self):
        relevant_param_choices = [
            [(param, choice) for choice in param.type.choices]
            for param in self.params
            if isinstance(param.type, click.Choice)
            and getattr(param.type, "_reproduci_is_slurm_param", False)
        ]
        return list(itertools.product(*relevant_param_choices))

    def schedule(self):
        return [
            SCHEDULE_COMMAND,
            *self.slurm_args,
            "--array=0-" + str(len(self.slurm_configurations) - 1),
            "--",
            reroot(),
        ]

    def invoke(self, *args, **kwargs):
        if self.slurm_schedule:
            ctx = click.get_current_context()
            params = {param.name: param for param in self.params}
            for param_name, value in ctx.params.items():
                if not value:
                    continue
                param = params[param_name]
                if getattr(param.type, "_reproduci_is_slurm_param", False):
                    continue
                if isinstance(param, click.Option):
                    self.slurm_schedule.extend(
                        [
                            f"--{param_name.replace('_', '-')}",
                            str(value),
                        ]
                    )
                else:
                    self.slurm_schedule.append(
                        str(value),
                    )
            subprocess.run(self.slurm_schedule)
            raise SystemExit(0)

        super().invoke(*args, **kwargs)

def command(**kwargs):
    return click.command(cls=SlurmCommand, slurm=kwargs)
