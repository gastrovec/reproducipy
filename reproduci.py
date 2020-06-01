import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path
from collections import Counter
from datetime import datetime
from textwrap import dedent

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
@click.option("--allow-dirty", is_flag=True, default=True)
def store(tag, tee, allow_dirty):
    full_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    short_hash = full_hash[:7]
    is_dirty, has_untracked = get_git_status()
    dt = datetime.now().astimezone()
    header = {"Hash": full_hash, "Timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S.%f%z")}
    if is_dirty:
        if not allow_dirty:
            raise click.ClickException("git dirty, refusing to store")
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
@click.argument("commit-spec", required=False)
@click.option("--tag")
@click.option("--raw", "-r", is_flag=True)
def load(commit_spec, tag=None, raw=False):
    # try to find all results with that hash, and print them.
    # if a tag is given, filter on that tag
    if commit_spec is None:
        commit_spec = "HEAD"
    if commit_spec != "all":
        full_hash = (
            subprocess.check_output(["git", "rev-parse", commit_spec],).decode().strip()
        )
    short_hash = full_hash[:7]
    if tag is None:
        tags = Path("store").glob("*")
    else:
        tags = [Path("store") / tag]

    for the_tag in tags:
        if (
            not tag and not raw
        ):  # we are looking at several tags, therefore we print a header
            print("[{}]".format(the_tag.name))
        candidate_iter = (
            the_tag.glob("*")
            if commit_spec == "all"
            else the_tag.glob("*-{}*".format(short_hash))
        )
        for candidate in candidate_iter:
            with candidate.open() as f:
                past_empty_line = False
                for line in f:
                    if not line.strip():
                        past_empty_line = True
                        if raw:
                            continue
                    if not past_empty_line and raw:
                        continue
                    sys.stdout.write(line)
            if not raw:
                print()
                print()


@cli.command()
def stats():
    tags, commits = Counter(), Counter()
    dirty, total = 0, 0
    max_date, min_date = None, None
    for tag in Path("store").glob("*"):
        for file in tag.glob("*"):
            ts, _, rest = file.name.partition("-")
            commit_hash, _, dirt = rest.partition("-")
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            if max_date is None or dt > max_date:
                max_date = dt
            if min_date is None or dt < min_date:
                min_date = dt
            commits[commit_hash] += 1
            tags[tag.name] += 1
            dirty += bool(dirt)
            total += 1
    top_commits = ", ".join(commit for commit, _ in commits.most_common(3))
    top_tags = ", ".join(tag for tag, _ in tags.most_common(3))
    print(
        dedent(
            f"""
            Stored {total} results in total, {dirty} from dirty commits.
            Earliest: {str(min_date)} Latest: {str(max_date)}
            {len(tags)} tags in total, most common: {top_tags}
            {len(commits)} commits in total, most common: {top_commits}
            """
        ).strip("\n")
    )


if __name__ == "__main__":
    cli()
