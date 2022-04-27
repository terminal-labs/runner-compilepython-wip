import os
import sys
import time
import json
import yaml
import shutil
import hashlib
import zipfile
import base64
import uuid
import sys
from pathlib import Path

import click

from cli_passthrough import cli_passthrough

VERSION = "0.1"
PROJECT_NAME = "noderunner"
context_settings = {"help_option_names": ["-h", "--help"]}

client_up = '.tmp/client/up/'
client_down = '.tmp/client/down/'
server_up = '.tmp/server/up/'
server_down = '.tmp/server/down/'
server_jobs = '.tmp/server/jobs/'
server_workspace = '.tmp/server/workspace/'

tmp_dirs = [
    ".tmp/",
    ".tmp/client",
    ".tmp/server",
    client_up,
    client_down,
    server_up,
    server_down,
    server_jobs,
    server_workspace,
    '.tmp/runners/'
    ]


def updt(total, progress):
    """
    Displays or updates a console progress bar.

    Original source: https://stackoverflow.com/a/15860757/1391441
    """
    barLength, status = 20, ""
    progress = float(progress) / float(total)
    if progress >= 1.:
        progress, status = 1, "\r\n"
    block = int(round(barLength * progress))
    text = "\r[{}] {:.0f}% {}".format(
        "#" * block + "-" * (barLength - block), round(progress * 100, 0),
        status)
    sys.stdout.write(text)
    sys.stdout.flush()


def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()

def remove(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
        if os.path.isdir(path):
            shutil.rmtree(path)

def create_dirs(dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

def initprocess():
    return {
        "historyfile": "/history.log",
        "stderrfile": "/hstderr.log",
        "linesfile": "/sg.lines",
        "eventsfile": "/sg.events",
    }

def run(uuid_name):
    sys.stdout = open('.tmp/runners/runs/' + uuid_name + "/process.out", "w")
    sys.stderr = open('.tmp/runners/runs/' + uuid_name + "/process.err", "w")

    cli_passthrough("bash examples/processes/compilepython/00.sh")
    cli_passthrough("bash examples/processes/compilepython/01.sh")
    cli_passthrough("bash examples/processes/compilepython/02.sh")

@click.group(context_settings=context_settings)
@click.version_option(prog_name=PROJECT_NAME.capitalize(), version=VERSION)
@click.pass_context
def cli(ctx):
    pass

@click.group(name="runners")
def run_group():
    pass

@run_group.command("run")
def run_cmd():
    create_dirs(tmp_dirs)

    import uuid
    uuid_name = uuid.uuid4().hex

    dir = '.tmp/runners/'
    if not os.path.exists(dir):
        os.mkdir(dir)

    dir = '.tmp/runners/runs'
    if not os.path.exists(dir):
        os.mkdir(dir)

    dir = '.tmp/runners/runs/' + uuid_name
    if not os.path.exists(dir):
        os.mkdir(dir)
    processinfo = initprocess()

    with open('examples/processes/compilepython/checkpointlines') as f:
        checkpointlines = f.readlines()
        checkpointlines = [s.strip() for s in checkpointlines]

    with open('.tmp/runners/runs/' + uuid_name + "/process.lines", 'w') as f:
        f.write("")
    with open('.tmp/runners/runs/' + uuid_name + "/process.events", 'w') as f:
        f.write("")
    import multiprocessing
    import sys

    p1 =  multiprocessing.Process(target=run, args=(uuid_name,))
    p1.start()

    runs = 3
    count = 0
    updt(runs, count)
    while count <= runs - 1:
        time.sleep(1)
        with open('.tmp/runners/runs/' + uuid_name + "/process.out") as f:
            lines = f.readlines()
            lines = [s.strip() for s in lines]
            count = 0
            for line in checkpointlines:
                if line in lines:
                    count = count + 1
                    updt(runs, count)

cli.add_command(run_group)
