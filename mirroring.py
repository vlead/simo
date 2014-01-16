
import os
import re
import subprocess
import sys
import json
import logging
from logging.handlers import TimedRotatingFileHandler

import requests
from requests.auth import HTTPBasicAuth

from bb_settings import *

PATH = "/labs/"
BB_URL = "https://bitbucket.org/virtuallabs/"
BB_PUSH_URL = "ssh://git@altssh.bitbucket.org:443/virtuallabs/"
BB_PUSH_URL2 = "git+ssh://git@altssh.bitbucket.org:443/virtuallabs/"
GIT_LOCATE = r"find %s -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "git")
BZR_LOCATE = r"find %s -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "trunk")
SVN_LOCATE = r"find %s -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "svn")
LAB_ID_REGEX = r"\w+\d*"
GIT_SVN_REPO_LOCATION = "./git-svn-dir/"

SIMO_LOGGER = logging.getLogger('simo')

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
    all_git_locations = subprocess.check_output(GIT_LOCATE, shell=True)
    for location in all_git_locations.split('\n'):
        # get all the git repo names 
        m = re.match("/labs/(%s)/" % LAB_ID_REGEX, location)
        if m == None:
            continue
        lab_name = m.group(1)
        for repo_name in os.listdir(location):
            # form the bitbucket repo url
            SIMO_LOGGER.debug("Now working on Git repo %s" % repo_name)
            bb_repo_name = (lab_name + "-" + repo_name).lower()
            repo_path = location + "/" + repo_name
            bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
            if bb_repo_exists(bb_repo_url):
                git_push(repo_path, bb_repo_name)
            else:
                SIMO_LOGGER.debug("Creating Bitbucket repo %s" % bb_repo_name)
                if create_bb_repo(bb_repo_name):
                    git_push(repo_path, bb_repo_name)
    SIMO_LOGGER.info(
        "Finished uploading git repositories. See the log file for any errors")

def git_push(repo_path, repo_name):
    repo_url = '%s%s' % (BB_PUSH_URL,repo_name)
    git_command = "git --git-dir=%s push %s master" % (repo_path, repo_url)
    try:
        subprocess.check_call(git_command, shell=True)
    except Exception, e:
        SIMO_LOGGER.error('push failed for', repo_name)
        SIMO_LOGGER.error(e.message)

def bb_repo_exists(repo_url):
    auth = HTTPBasicAuth(BB_USERNAME, BB_PASSWORD)
    response = requests.get(url=repo_url, auth=auth)
    return response.status_code == requests.codes.ok

def create_bb_repo(repo_name):
    auth = HTTPBasicAuth(BB_USERNAME, BB_PASSWORD)
    # https://api.bitbucket.org/2.0/repositories/BB_USERNAME/repo_name
    url = '%s%s/%s' % (REPO_API_URL, BB_USERNAME, repo_name)
    payload = { "scm": "git", "is_private": "true"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url=url, data=payload, auth=auth)
    if response.status_code != requests.codes.ok:
        SIMO_LOGGER.error(
            "Received status code %s on creating Bitbucket repo %s",
            response.status_code, repo_name)
        return False
    return True

def bzr_push(repo_path, repo_name):
    repo_url = '%s%s' % (BB_PUSH_URL2, repo_name)
    git_command = "bzr dpush -d %s %s,branch=master " % \
                                            (repo_path, repo_url)
    try:
        subprocess.check_call(git_command, shell=True)
    except Exception, e:
        SIMO_LOGGER.error('push failed for', repo_name)
        SIMO_LOGGER.error(e.message)

def upload_bzr_repos():
    all_bzr_locations = subprocess.check_output(BZR_LOCATE, shell=True)
    for location in all_bzr_locations.split('\n'):
        # get all the bazaar repo names 
        m = re.match(r'/labs/(\w+\d*)/bzr/([\w\d\-_]+)/', location)
        if m == None:
            continue
        lab_name = m.group(1)
        repo_name = m.group(2)
        SIMO_LOGGER.debug("Now working on Bazaar repo %s" % repo_name)
        # form the bitbucket repo url
        bb_repo_name = (lab_name + "-" + repo_name).lower()
        repo_path = location #+ "/" + repo_name
        bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
        if bb_repo_exists(bb_repo_url):
            bzr_push(repo_path, bb_repo_name)
        else:
            SIMO_LOGGER.debug("Creating Bitbucket repo %s" % bb_repo_name)
            if create_bb_repo(bb_repo_name):
                bzr_push(repo_path, bb_repo_name)
    SIMO_LOGGER.info(
        "Finished uploading Bazaar repositories. See the log file for any errors")

def upload_svn_repos():
    all_svn_locations = subprocess.check_output(SVN_LOCATE, shell=True)
    for location in all_svn_locations.split('\n'):
        m = re.match("/labs/(%s)/svn" % LAB_ID_REGEX, location)
        if m == None:
            continue
        lab_name = m.group(1)
        for repo_name in filter(os.path.isdir, os.listdir(location)):
            SIMO_LOGGER.debug("Now working on Subversion repo %s" % repo_name)
            bb_repo_name = (lab_name + "-" + repo_name).lower()
            repo_path = location + "/" + repo_name
            bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
            git_repo_path = os.getcwd() + "/" + GIT_SVN_REPO_LOCATION + \
                            bb_repo_name + "/.git"
            if os.path.exists(git_repo_path):
                sync_svn_git(bb_repo_name)
                git_push(git_repo_path, bb_repo_name)
            else:
                SIMO_LOGGER.debug("Creating local git repo for this svn repo")
                create_git_from_svn(repo_path, bb_repo_name)
            if not bb_repo_exists(bb_repo_url):
                SIMO_LOGGER.debug("Creating Bitbucket repo %s" % bb_repo_name)
                if create_bb_repo(bb_repo_name):
                    git_push(git_repo_path, bb_repo_name)
    SIMO_LOGGER.info(
        "Finished uploading Subversion repositories. See the log file for any errors")

def sync_svn_git(repo_name):
    git_work_tree = GIT_SVN_REPO_LOCATION + repo_name
    orig_dir = os.getcwd()
    os.chdir(git_work_tree)
    try:
        subprocess.check_call("git svn fetch", shell=True)
        subprocess.check_call("git svn rebase", shell=True)
    except Exception, e:
        SIMO_LOGGER.error('svn sync failed for', repo_name)
        SIMO_LOGGER.error(e.message)
    finally:
        os.chdir(orig_dir)

def create_git_from_svn(repo_path, bb_repo_name):
    """Creates a local git repo from svn"""
    GIT_SVN_CLONE = "git svn clone file://%s %s" % (repo_path, 
                                        GIT_SVN_REPO_LOCATION + bb_repo_name)
    try:
        subprocess.check_call(GIT_SVN_CLONE, shell=True)
    except Exception, e:
        SIMO_LOGGER.error('git svn clone failed for', bb_repo_name)
        SIMO_LOGGER.error(e.message)

def setup_logging():
    LOG_FILENAME = 'log/simo.log'       # make log name a setting
    
    SIMO_LOGGER.setLevel(logging.DEBUG)   # make log level a setting

    # Add the log message handler to the logger
    handler = logging.handlers.TimedRotatingFileHandler(
                                LOG_FILENAME, when='midnight', backupCount=5)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %I:%M:%S %p')
    handler.setFormatter(formatter)
    SIMO_LOGGER.addHandler(handler)

if __name__ == '__main__':
    setup_logging()
    SIMO_LOGGER.info("*****Started SIMO*****")
    upload_git_repos()
    upload_bzr_repos()
    upload_svn_repos()
    SIMO_LOGGER.info("*****Finished SIMO*****")
