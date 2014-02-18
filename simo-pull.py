import json
import os
import subprocess
import shlex
import logging
from logging.handlers import TimedRotatingFileHandler

import requests
from requests.auth import HTTPBasicAuth

from simo_pull_settings import *

SIMO_LOGGER = logging.getLogger('SIMO-PULL')


def get_bb_repo_info():
    def make_rest_call(url):
        auth = HTTPBasicAuth(BB_USERNAME, BB_PASSWORD)
        return requests.get(url=url, auth=auth).json()

    base_url = 'https://bitbucket.org/api/2.0/repositories/'
    seed_url = base_url + TEAM_NAME
    response = make_rest_call(seed_url)
    bb_repo_info = []

    while True:
        for repo in response['values']:
            bb_repo_info.append((repo['name'], repo['links']['html']['href']))
        if not 'next' in response.keys():
            break
        response = make_rest_call(response['next'])
    
    return bb_repo_info


def sync_solutions(repo_name):
    def repo_exists(repo_name):
        return os.path.isdir(REPOS_DIR + repo_name)

    def clone_repo(repo_name):
        clone_cmd = shlex.split("git clone %s%s %s%s" % (BB_REPO_BASE_URL, 
                                 repo_name, REPOS_DIR, repo_name))
        try:
            subprocess.check_call(clone_cmd, stdout=LOG_FD, stderr=LOG_FD)
        except Exception, e:
            SIMO_LOGGER.error('clone failed for repo %s: %s', repo_name, str(e))

    def pull_repo(repo_name):
        pull_cmd = shlex.split("git --git-dir=%s/.git pull" % \
                            (REPOS_DIR + repo_name))
        try:
            subprocess.check_call(pull_cmd, stdout=LOG_FD, stderr=LOG_FD)
        except Exception, e:
            SIMO_LOGGER.error('pull failed for repo %s: %s', repo_name, str(e))

    if repo_exists(repo_name):
        pull_repo(repo_name)
    else:
        clone_repo(repo_name)


def setup_logging():
    SIMO_LOGGER.setLevel(logging.DEBUG)   # make log level a setting
    # Add the log message handler to the logger
    myhandler = TimedRotatingFileHandler(LOGS_DIR+LOG_FILENAME, when='midnight', 
                                        backupCount=5)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %I:%M:%S %p')
    myhandler.setFormatter(formatter)
    SIMO_LOGGER.addHandler(myhandler)


def main():
    for repo_name, repo_url in get_bb_repo_info():
        SIMO_LOGGER.debug(repo_name)
        sync_solutions(repo_name)


if __name__ == '__main__':
    if not os.path.isdir(LOGS_DIR):
        os.mkdir(LOGS_DIR)
    if not os.path.isdir(REPOS_DIR):
        os.mkdir(REPOS_DIR)
    LOG_FD = open(LOGS_DIR+LOG_FILENAME, 'a')
    setup_logging()
    SIMO_LOGGER.debug('****Started SIMO****')
    main()
    SIMO_LOGGER.debug('****Finished SIMO****')
