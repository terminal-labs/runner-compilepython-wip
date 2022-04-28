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

import requests
import click

from cli_passthrough import cli_passthrough

from jobrunner.progressengine import updt, register_run, get_checkpointlines, track_run, get_track_data
from jobrunner.config import tmp_dirs
from jobrunner.utils import remove, create_dirs, init_runner_env
from jobrunner.core import app, simplejob

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

def kickoff_tracker(uuid_name, checkpointlines):
    p1 =  multiprocessing.Process(target=track_run, args=(uuid_name, checkpointlines, False,))
    p1.start()

def run(uuid_name, capturelogs=False):
    if capturelogs:
        sys.stdout = open('.tmp/runners/runs/' + uuid_name + "/process.out", "w")
        sys.stderr = open('.tmp/runners/runs/' + uuid_name + "/process.err", "w")

    cli_passthrough("bash examples/processes/compilepython/00.sh")
    cli_passthrough("bash examples/processes/compilepython/01.sh")
    cli_passthrough("bash examples/processes/compilepython/02.sh")

@app.route('/track')
def urltrack():
    init_runner_env()
    uuid_name, checkpointlines = pre_run()
    kickoff_run(uuid_name)
    kickoff_tracker(uuid_name, checkpointlines)
    return {"uuid_name": uuid_name}

@app.route('/status/<uuid_name>')
def urlstatus(uuid_name):
    return get_track_data(uuid_name)

@click.group(context_settings=context_settings)
@click.version_option(prog_name=PROJECT_NAME.capitalize(), version=VERSION)
@click.pass_context
def cli(ctx):
    pass

@click.group(name="runner")
def run_group():
    pass

@run_group.command("run")
def run_cmd():
    init_runner_env()
    uuid_name, checkpointlines = pre_run()
    run(uuid_name)

@run_group.command("track")
def track_cmd():
    init_runner_env()
    uuid_name, checkpointlines = pre_run()
    kickoff_run(uuid_name)
    time.sleep(1)
    track_run(uuid_name, checkpointlines, pbar=False)

@run_group.command("pbar")
def pbar_cmd():
    init_runner_env()
    uuid_name, checkpointlines = pre_run()
    kickoff_run(uuid_name)
    time.sleep(1)
    track_run(uuid_name, checkpointlines, pbar=True)

@click.group(name="server")
def server_group():
    pass

@server_group.command("serve")
def serve_cmd():
    app.run(debug=True, port=8080)

@click.group(name="client")
def client_group():
    pass

@client_group.command("pbar")
def client_pbar_cmd():
    def __track():
        r = requests.get('http://127.0.0.1:8080/track')
        message = r.json()
        uuid_name = message["uuid_name"]
        return message


    def __get_status():
        r = requests.get('http://127.0.0.1:8080/status/' + uuid_name)
        message = r.json()
        runs = message["runs"]
        count = message["count"]
        return runs, count

    message = __track()
    uuid_name = message["uuid_name"]

    runs, count = __get_status()
    updt(runs, count)
    while count <= runs - 1:
        runs, count = __get_status()
        updt(runs, count)
        time.sleep(1)

cli.add_command(server_group)
cli.add_command(client_group)
cli.add_command(run_group)
