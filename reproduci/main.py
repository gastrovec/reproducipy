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


@cli.command(help="Initialize a reproduci project (create folders and do a `git init`)")
@click.option(
    "--all",
    "-a",
    "all_",
    is_flag=True,
    help="Create folders that are not always needed (writing, persistent)",
)
def init(all_):
    folders = ["sources", "workdata", "outputs", "scripts"]
    if all_:
        folders.extend(["writing", "persistent"])
    for folder in folders:
        Path(folder).mkdir(exist_ok=True)
    Path("Makefile").touch()
    assert subprocess.call(["git", "init"]) == 0


@cli.command(
    help="Store data in the internal store, annotated with timestamp, tag, and commit"
)
@click.argument("tag")
@click.option(
    "--tee", is_flag=True, help="Forward stdin to stdout in addition to storing"
)
@click.option(
    "--allow-dirty/--no-allow-dirty",
    is_flag=True,
    default=True,
    help="Allow storing of data even if Git is dirty.",
)
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


@cli.command(help="Retrieve data from the internal store")
@click.argument("commit-spec", required=False)
@click.option(
    "--tag", help="A tag to filter for. If not given, shows results from all tags"
)
@click.option(
    "--raw", "-r", is_flag=True, help="Don't print headers or seperating newlines"
)
@click.option(
    "--show-dirty/--no-show-dirty",
    is_flag=True,
    default=True,
    help="Allow results from dirty Git states to be shown",
)
def load(commit_spec, tag, raw, show_dirty):
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
        candidate_iter = (
            the_tag.glob("*")
            if commit_spec == "all"
            else the_tag.glob("*-{}*".format(short_hash))
        )
        for candidate in candidate_iter:
            buffer = []
            if not raw:
                buffer.append("[{}]\n".format(the_tag.name))
            with candidate.open() as f:
                past_empty_line = False
                for line in f:
                    if not line.strip():
                        past_empty_line = True
                        if raw:
                            continue
                    if not past_empty_line:
                        key, _, val = line.partition(": ")
                        if key == "Dirty" and val.strip() == "1" and not show_dirty:
                            break
                        if raw:
                            continue
                    buffer.append(line)
                else:
                    for line in buffer:
                        sys.stdout.write(line)

                    if not raw:
                        print()
                        print()


@cli.command(help="Show some stats on the internal store")
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
