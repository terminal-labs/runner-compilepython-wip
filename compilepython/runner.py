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
import multiprocessing
from pathlib import Path

import click

from cli_passthrough import cli_passthrough

from jobrunner.progressengine import updt, register_run, get_checkpointlines, pbar
from jobrunner.config import tmp_dirs
from jobrunner.utils import remove, create_dirs, init_runner_env

VERSION = "0.1"
PROJECT_NAME = "compilepython"
context_settings = {"help_option_names": ["-h", "--help"]}

def pre_run():
    uuid_name = uuid.uuid4().hex
    register_run(uuid_name)
    checkpointlines = get_checkpointlines('examples/processes/compilepython/checkpointlines')
    return uuid_name, checkpointlines

def kickoff_run(uuid_name):
    p1 =  multiprocessing.Process(target=run, args=(uuid_name, True,))
    p1.start()

def run(uuid_name, capturelogs=False):
    if capturelogs:
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
    init_runner_env()
    uuid_name, checkpointlines = pre_run()
    run(uuid_name)

@run_group.command("pbar")
def pbar_cmd():
    init_runner_env()
    uuid_name, checkpointlines = pre_run()
    kickoff_run(uuid_name)
    time.sleep(1)
    pbar(uuid_name, checkpointlines)

cli.add_command(run_group)
