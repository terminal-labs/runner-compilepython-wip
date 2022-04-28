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
from flask import Flask, jsonify, request, send_from_directory

from cli_passthrough import cli_passthrough

from jobrunner.progressengine import updt, register_run, get_checkpointlines, track_run, get_track_data
from jobrunner.config import tmp_dirs
from jobrunner.utils import remove, create_dirs, init_runner_env
from jobrunner.core import app, simplejob, from_message, get_message_localserve, creatzip

VERSION = "0.1"
PROJECT_NAME = "compilepython"
context_settings = {"help_option_names": ["-h", "--help"]}

def pre_run(uuid_name=None):
    if not uuid_name:
        uuid_name = uuid.uuid4().hex
    create_dirs([".tmp",".tmp/processes", ".tmp/processes/"  + uuid_name])
    create_dirs([".tmp",".tmp/runners", ".tmp/runners/runs"])
    create_dirs(tmp_dirs)


    test00 = """
wget https://www.python.org/ftp/python/3.6.9/Python-3.6.9.tgz
    """
    with open(".tmp/processes/"  + uuid_name + "/00.sh", 'w') as f:
        f.write(test00)

    test01 = """
tar xzf Python-3.6.9.tgz
    """
    with open(".tmp/processes/"  + uuid_name + "/01.sh", 'w') as f:
        f.write(test01)

    test02 = """
cd Python-3.6.9
./configure --enable-optimizations
    """
    with open(".tmp/processes/"  + uuid_name + "/02.sh", 'w') as f:
        f.write(test02)

    checkpointeventsfile = """
checking build system type...
checking whether we are using the GNU C compiler...
    """
    with open(".tmp/processes/"  + uuid_name + "/checkpointevents", 'w') as f:
        f.write(checkpointeventsfile)

    checkpointlinessfile = """
checking build system type...
checking for --with-undefined-behavior-sanitizer...
creating Makefile
    """
    with open(".tmp/processes/"  + uuid_name + "/checkpointlines", 'w') as f:
        f.write(checkpointlinessfile)

    register_run(uuid_name)
    checkpointlines = get_checkpointlines(".tmp/processes/"  + uuid_name + '/checkpointlines')
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

    create_dirs([".tmp",".tmp/processes", ".tmp/processes/"  + uuid_name])
    os.chdir(".tmp/processes/"  + uuid_name)

    cli_passthrough("bash 00.sh")
    cli_passthrough("bash 01.sh")
    cli_passthrough("bash 02.sh")

@app.route('/api/preppackage', methods=['POST'])
def preppackage():
    message = request.json
    payload_obj = from_message(message)
    name = payload_obj["name"]
    uuid_name = payload_obj["uuid_name"]
    jobid = payload_obj["jobid"]
    get_message_localserve(message)
    return {}

@app.route('/prepdelivery/<uuid_name>',)
def prepdelivery(uuid_name):
    create_dirs(tmp_dirs)
    print("got it")
    creatzip(".tmp/server/workspace/" + uuid_name, ".tmp/processes/"  + uuid_name)
    return {}

@app.route('/builds/<uuid_name>')
def builds_func(uuid_name):
    return send_from_directory(os.path.abspath(os.getcwd()) + "/.tmp/server/workspace", uuid_name)

@app.route('/track')
@app.route('/track/<uuid_name>')
def urltrack(uuid_name=None):
    init_runner_env()
    uuid_name, checkpointlines = pre_run(uuid_name)
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
