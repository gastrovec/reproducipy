# reproducipy

This is a companion tool to the [*reproduci* methodology](https://github.com/gastrovec/reproduci).


## Installation

```
pip install reproduci
```

## Initializing a reproduci project

By running

```
reproduci init
```

a new Git repo will be created with the basic folder and file structure of
reproduci in place.

## Using the store

Pipe data (for example results) into `reproduci store` with some tag name,
refering to the type of data to store:

```
$ echo some result | reproduci store main-result
          ^                               ^
    Programm output                Arbitrary tag
```

The output of the program will be saved alongside the current git commit hash,
timestamp, and tag in the internal `store/` directory.


To retrieve data from the store, use `reproduci load` with some git reference
(usually a commit hash; see the section called "SPECIFYING REVISIONS" in the
manpage of `git-rev-parse` for details):

```
$ reproduci load  # print latest results across all tags
$ reproduci load --tag main-result  # print latest results from tag "main-result"
$ reproduci load abcdefg  # print results from commit with hash abcdefg...
```

## Use as a Python module

No matter from where you call your scripts, `reproduci.ROOT` will always point
to the main project directory (it's a `pathlib.Path`).

### Slurm support

reproducipy has basic support for the [slurm workload manager](https://slurm.schedmd.com/):

In its simplest form, you can set options for how to run the script via slurm:

```python
from reproduci import slurm

slurm.simple(
    time=15,
    partition="my_partition",
    job_name="example script",
)

When run directly, this script will schedule itself with `sbatch --time 15
--job-name 'example script'` (the keyword arguments of `slurm.simple` are run
through a simple translation (converting underscores to dashes) and handed
directly to `sbatch`), and exit immediately afterwards (any code written
_after_ `slurm.simple()` will not be executed).

When slurm runs the script, it doesn't schedule itself again, but simply
continues executing the code.

In essense, this allows you to schedule your scripts by just attempting to run
them directly.

We also support the `--job-array` option with some magic:

```python
from reproduci import slurm

color, taste = slurm.multi(
    (color, taste for color in ("red", "green") for taste in ("sweet", "sour", "salty")),
    time=5,
    partition="my_partition",
)
```

This schedules a job array of size six, one for each combination of color and
taste. The first argument to `slurm.multi` is just an arbitrary iterable.

The scheduled parts figure out which sub-job they are (slurm informs us of that
information via environment variables) and returns the corresponding values. In
our example, that means that in one run, `color` is `"red"` and `taste` is
`"sweet"`, in the second one it's `"red"` and `"sour"`, and so on.
`slurm.multi()` abstracts the plumbing of job arrays away from the user.

### Slurm ❤️ click

An alternative interface to the slurm integration is using `click`:

```python
import click
from reproduci import slurm

@slurm.command(time=5, partition="my_partition")
@click.option("--color", type=slurm.Choice(["red", "green"]))
@click.option("--taste", type=slurm.Choice(["sweet", "sour", "salty"]))
@click.option("--frobnication")
def cli(color, taste, frobnication):
    ...
```

TL;DR: Use `slurm.command()` instead of `click.command()`, and use options of
the type `slurm.Choice` to parametrize over them. Options and arguments that
aren't of the type `slurm.Choice` are left alone and given to the scheduled
jobs. Note that fancy callback logic can break all of this, don't use that kind
of thing here.

The way you'd schedule this is by calling the script and passing in any
*non-slurmed* options and arguments. Leave the slurmed options alone; don't
pass any values for them (we take care of that).
