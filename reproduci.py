import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

import click


def get_git_status():
    is_dirty = has_untracked = False
    git_status = (
        subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
    )
    for line in git_status.split("\n"):
        flags, _, __ = line.strip().partition(" ")
        if "M" in flags:
            is_dirty = True
            continue
        if "?" in flags:
            has_untracked = True
            continue
    return is_dirty, has_untracked


@click.group()
def cli():
    pass


@cli.command()
def init():
    for top_level_dir in ["sources", "workdata", "results", "scripts", "store"]:
        os.makedirs(top_level_dir, exist_ok=True)
    with open("Makefile", "w") as f:
        f.write("")
    assert subprocess.call(["git", "init"]) == 0


@cli.command()
@click.argument("tag")
@click.option("--tee", is_flag=True)
def store(tag, tee):
    full_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    short_hash = full_hash[:7]
    is_dirty, has_untracked = get_git_status()
    dt = datetime.now().astimezone()
    header = {"Hash": full_hash, "Timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S.%f%z")}
    if is_dirty:
        header["Dirty"] = 1
    if has_untracked:
        header["HasUntracked"] = 1
    filename = "{}-{}{}".format(
        dt.strftime("%Y%m%d%H%M%S"), short_hash, "-dirty" if is_dirty else ""
    )
    os.makedirs("store/{}".format(tag), exist_ok=True)
    with open("store/{}/{}".format(tag, filename), "w") as f:
        for key, value in header.items():
            f.write("{}: {}\n".format(key, str(value)))
        f.write("\n")
        for line in sys.stdin:
            f.write(line)
            if tee:
                sys.stdout.write(line)
    if is_dirty:
        raise click.ClickException("git dirty, saved as {}/{}".format(tag, filename))


@cli.command()
@click.argument("short_hash")
@click.option("--tag")
def load(short_hash, tag=None):
    # try to find all results with that hash, and print them.
    # if a tag is given, filter on that tag
    if tag is None:
        tags = Path("store").glob("*")
    else:
        tags = [Path("store") / tag]

    for the_tag in tags:
        if not tag:  # we are looking at several tags, therefore we print a header
            print("[{}]".format(the_tag.name))
        for candidate in the_tag.glob("*-{}*".format(short_hash)):
            with candidate.open() as f:
                for line in f:
                    sys.stdout.write(line)


if __name__ == "__main__":
    cli()
