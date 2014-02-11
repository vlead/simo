
import os
import re
import subprocess
import sys
import json
import logging
import datetime
from logging.handlers import TimedRotatingFileHandler

import requests
from requests.auth import HTTPBasicAuth

from bb_settings import *
from mailman import mailer

PATH = "/labs/"
BB_URL = "https://bitbucket.org/virtuallabs/"
BB_PUSH_URL = "ssh://git@altssh.bitbucket.org:443/virtuallabs/"
BB_PUSH_URL2 = "git+ssh://git@altssh.bitbucket.org:443/virtuallabs/"
GIT_LOCATE = r"find %s -maxdepth 3 -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "git")
BZR_LOCATE = r"find %s -maxdepth 5 -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "trunk")
SVN_LOCATE = r"find %s -maxdepth 3 -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "svn")
LAB_ID_REGEX = r"\w+\d*"
GIT_SVN_REPO_LOCATION = "./git-svn-dir/"
GIT_SVN_FETCH = "git svn fetch"
GIT_SVN_REBASE = "git svn rebase"

SIMO_LOGGER = logging.getLogger('simo')
LOG_FILENAME = 'log/simo.log'       # make log name a setting

def upload_git_repos():
    """Upload all git repos at PATH
    1. Get all the directory names containing git repos
        - run Find command ( find -name git -exec du -sh {} \; | grep -v "^4.0K" )
        - parse the output & get the path 
        - find out all the repositories within that directory
    2. Change pwd to repository 
        - Check if the BB remote has been set or not.
        - If set, continue to next step 
        - If not, create a repo on BB with the lab name
            - The labname is 'grandparent directory' + '-' + 'pwd'
            - the upstream would be :
                https://bitbucket.org/vlabs/grandparent-lab
            - set the upstream
    4. Do git push
    5. change pwd back to PATH
    6. Repeat 2-6 for each repo
    """
    SIMO_LOGGER.debug(GIT_LOCATE)
    all_git_locations = subprocess.check_output(GIT_LOCATE, shell=True)
    for location in all_git_locations.split('\n'):
        # get all the git repo names 
        m = re.match("/labs/(%s)/" % LAB_ID_REGEX, location)
        if m == None:
            continue
        lab_name = m.group(1)
        for repo_name in os.listdir(location):
            # form the bitbucket repo url
            SIMO_LOGGER.info("Now working on Git repo '%s'" % repo_name)
            bb_repo_name = (lab_name + "-" + repo_name).lower()
            repo_path = location + "/" + repo_name
            bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
            if bb_repo_exists(bb_repo_url):
                git_push(repo_path, bb_repo_name)
            else:
                if create_bb_repo(bb_repo_name):
                    git_push(repo_path, bb_repo_name)
    SIMO_LOGGER.info(
        "Finished uploading git repositories. See the log file for any errors")

def git_push(repo_path, repo_name):
    repo_url = '%s%s' % (BB_PUSH_URL,repo_name)
    git_command = "git --git-dir=%s push %s master" % (repo_path, repo_url)
    SIMO_LOGGER.debug(git_command)
    try:
        subprocess.check_call(git_command, shell=True, stdout=LOG_FD,  
                            stderr=LOG_FD)
    except Exception, e:
        SIMO_LOGGER.error('push failed for %s ' % repo_name + str(e))

def bb_repo_exists(repo_url):
    SIMO_LOGGER.debug("Looking up Bitbucket for repo " + repo_url)
    auth = HTTPBasicAuth(BB_USERNAME, BB_PASSWORD)
    response = requests.get(url=repo_url, auth=auth)
    return response.status_code == requests.codes.ok

def create_bb_repo(repo_name):
    SIMO_LOGGER.debug("Creating Bitbucket repo '%s'" % repo_name)
    auth = HTTPBasicAuth(BB_USERNAME, BB_PASSWORD)
    # https://api.bitbucket.org/2.0/repositories/BB_USERNAME/repo_name
    url = '%s%s/%s' % (REPO_API_URL, BB_USERNAME, repo_name)
    payload = { "scm": "git", "is_private": "true"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url=url, data=payload, auth=auth)
    if response.status_code != requests.codes.ok:
        SIMO_LOGGER.error(
            "Received status code '%s' on creating Bitbucket repo '%s' " %
            (response.status_code, repo_name))
        return False
    return True

def bzr_push(repo_path, repo_name):
    repo_url = '%s%s' % (BB_PUSH_URL2, repo_name)
    bzr_command = "bzr dpush --directory=%s %s,branch=master" % \
                                            (repo_path, repo_url)
    SIMO_LOGGER.debug(bzr_command)
    try:
        subprocess.check_call(bzr_command, shell=True, stdout=LOG_FD,  
                            stderr=LOG_FD)
    except Exception, e:
        SIMO_LOGGER.error('push failed for %s ' % repo_name + str(e))

def upload_bzr_repos():
    SIMO_LOGGER.debug(BZR_LOCATE)
    all_bzr_locations = subprocess.check_output(BZR_LOCATE, shell=True)
    for location in all_bzr_locations.split('\n'):
        # get all the bazaar repo names 
        m = re.match(r'/labs/(\w+\d*)/bzr/([\w\d\-_]+)/', location)
        if m == None:
            continue
        lab_name = m.group(1)
        repo_name = m.group(2)
        SIMO_LOGGER.info("Now working on Bazaar repo '%s'" % repo_name)
        # form the bitbucket repo url
        bb_repo_name = (lab_name + "-" + repo_name).lower()
        repo_path = location #+ "/" + repo_name
        bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
        if bb_repo_exists(bb_repo_url):
            bzr_push(repo_path, bb_repo_name)
        else:
            if create_bb_repo(bb_repo_name):
                bzr_push(repo_path, bb_repo_name)
    SIMO_LOGGER.info(
        "Finished uploading Bazaar repositories. See the log file for any errors")

def upload_svn_repos():
    SIMO_LOGGER.debug(SVN_LOCATE)
    all_svn_locations = subprocess.check_output(SVN_LOCATE, shell=True)
    for location in all_svn_locations.split('\n'):
        m = re.match("/labs/(%s)/svn" % LAB_ID_REGEX, location)
        if m == None:
            continue
        lab_name = m.group(1)
        for repo_name in os.listdir(location):
            SIMO_LOGGER.info("Now working on Subversion repo '%s'" % repo_name)
            bb_repo_name = (lab_name + "-" + repo_name).lower()
            repo_path = location + "/" + repo_name
            if not os.path.isdir(repo_path):
                continue
            bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
            git_repo_path = os.getcwd() + "/" + GIT_SVN_REPO_LOCATION + \
                            bb_repo_name + "/.git"

            if not os.path.exists(git_repo_path) and not \
                    create_git_from_svn(repo_path, bb_repo_name):
                continue
            if not sync_svn_git(bb_repo_name):
                continue
            if bb_repo_exists(bb_repo_url):
                git_push(git_repo_path, bb_repo_name)
            elif create_bb_repo(bb_repo_name):
                git_push(git_repo_path, bb_repo_name)
    SIMO_LOGGER.info(
        "Finished uploading Subversion repositories. See the log file for any errors")

def sync_svn_git(repo_name):
    git_work_tree = GIT_SVN_REPO_LOCATION + repo_name
    orig_dir = os.getcwd()
    os.chdir(git_work_tree)
    try:
        SIMO_LOGGER.debug(GIT_SVN_FETCH)
        subprocess.check_call(GIT_SVN_FETCH, shell=True, 
                                stdout=LOG_FD,  stderr=LOG_FD)
        SIMO_LOGGER.debug(GIT_SVN_REBASE)
        subprocess.check_call(GIT_SVN_REBASE, shell=True,
                                stdout=LOG_FD,  stderr=LOG_FD)
        os.chdir(orig_dir)
        return True
    except Exception, e:
        SIMO_LOGGER.error('svn sync failed for %s ' % repo_name + str(e))
        os.chdir(orig_dir)
        return False

def create_git_from_svn(repo_path, bb_repo_name):
    """Creates a local git repo from svn"""
    git_svn_clone = "git svn clone file://%s %s" % (repo_path,
                                        GIT_SVN_REPO_LOCATION + bb_repo_name)
    SIMO_LOGGER.debug(git_svn_clone)
    try:
        subprocess.check_call(git_svn_clone, shell=True, stdout=LOG_FD,
                                stderr=LOG_FD)
        return True
    except Exception, e:
        SIMO_LOGGER.error('git svn clone failed for %s ' % bb_repo_name + str(e))
        return False

def setup_logging():
    SIMO_LOGGER.setLevel(logging.DEBUG)   # make log level a setting
    # Add the log message handler to the logger
    simo_handler = logging.handlers.TimedRotatingFileHandler(
                                LOG_FILENAME, when='midnight', backupCount=5)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %I:%M:%S %p')
    simo_handler.setFormatter(formatter)
    SIMO_LOGGER.addHandler(simo_handler)

def send_email():
    mailer(*parse_log_file())

def parse_log_file():
    try:
        log = open(LOG_FILENAME).readlines()
        log_start = 0
        for i, line in enumerate(log):
            if "Started SIMO" in line:      # Only the last SIMO run now considered
                log_start = i
        start_time = log[log_start].split(' - ')[0]
        end_time = log[-1].split(' - ')[0]
        elapsed_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %I:%M:%S %p") - \
                        datetime.datetime.strptime(start_time, "%Y-%m-%d %I:%M:%S %p")
        message_list = [line for line in log[log_start:] if 'simo - ERROR' in line]
        message = reduce(lambda x, y: x+y, message_list) if bool(message_list) else ""
        return (start_time, end_time, str(elapsed_time), len(message_list), message, LOG_FILENAME)
    except Exception, e:
        return (None, None, None, 0, "Error encountered", LOG_FILENAME)

def test():
    # write test cases here
    assert True


if __name__ == '__main__':
    try:
        setup_logging()
        LOG_FD = open(LOG_FILENAME, 'a')
        if LOG_FD == None:
            SIMO_LOGGER.error("Unable to open log file for subprocess.")
            SIMO_LOGGER.error("Subprocess will not be able to log stdout and " + \
                                "stderr messages.")
        SIMO_LOGGER.info("Started SIMO")
        try:
            upload_git_repos()
            upload_bzr_repos()
            upload_svn_repos()
        except Exception, e:
            SIMO_LOGGER.error("Error encountered: " + str(e))
        SIMO_LOGGER.info("Finished SIMO")
        LOG_FD.close()
    except Exception, e:
        SIMO_LOGGER.error("Error encountered: " + str(e))
    send_email()
