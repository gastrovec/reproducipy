# reproducipy

This is a companion tool to the [*reproduci* methodology](https://github.com/gastrovec/reproduci).


## Installation

    pip install reproduci

## Usage

Pipe data (for example results) into `reproduci store` with some tag name,
refering to the type of data to store:

    $ echo some result | reproduci store main-result
             ^                               ^
      Programm output                Arbitrary tag

The output of the program will be saved alongside the current git commit hash,
timestamp, and tag in the internal `store/` directory.


To retrieve data from the store, use `reproduci load` with some git reference
(usually a commit hash; see the section called "SPECIFYING REVISIONS" in the
manpage of `git-rev-parse` for details):

    $ reproduci load  # print latest results across all tags
    $ reproduci load --tag main-result  # print latest results from tag "main-result"
    $ reproduci load abcdefg  # print results from commit with hash abcdefg...
