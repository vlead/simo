
import os
import re
import subprocess
import sys
import json

import requests
from requests.auth import HTTPBasicAuth

from bb_settings import *

PATH = "/labs/"
BB_URL = "https://bitbucket.org/virtuallabs/"
BB_PUSH_URL = "ssh://git@altssh.bitbucket.org:443/virtuallabs/"
GIT_LOCATE = r"find %s -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "git")
BZR_LOCATE = r"find %s -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "trunk")
SVN_LOCATE = r"find %s -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "svn")
LAB_ID_REGEX = r"\w+\d*"

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
    print GIT_LOCATE
    all_git_locations = subprocess.check_output(GIT_LOCATE, shell=True)
    for location in all_git_locations.split('\n'):
        print location
        # get all the git repo names 
        m = re.match("/labs/(%s)/" % LAB_ID_REGEX, location)
        if m == None:
            continue
        lab_name = m.group(1)
        for repo_name in os.listdir(location):
            # form the bitbucket repo url
            bb_repo_name = (lab_name + "-" + repo_name).lower()
            repo_path = location + "/" + repo_name
            bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
            if repo_exists(bb_repo_url):
                print "Pushing to repo", bb_repo_name
                git_push(repo_path, bb_repo_name)
            else:
                print "Creating repo", bb_repo_name
                create_repo(bb_repo_name)
                print "Pushing to repo", bb_repo_name
                git_push(repo_path, bb_repo_name)

def git_push(repo_path, repo_name):
    repo_url = '%s%s' % (BB_PUSH_URL,repo_name)
    git_command = "git --git-dir=%s push %s master" % \
                                            (repo_path, repo_url)
    try:
        subprocess.check_call(git_command, shell=True)
    except Exception, e:
        raise e

def repo_exists(repo_url):
    auth = HTTPBasicAuth(BB_USERNAME, BB_PASSWORD)
    response = requests.get(url=repo_url, auth=auth)
    return response.status_code == requests.codes.ok

def create_repo(repo_name):
    print BB_USERNAME, BB_PASSWORD
    auth = HTTPBasicAuth(BB_USERNAME, BB_PASSWORD)
    # the request URL format is https://api.bitbucket.org/2.0/repositories/BB_USERNAME/repo_name
    url = '%s%s/%s' % (REPO_API_URL, BB_USERNAME, repo_name)
    print url
    payload = { "scm": "git", "is_private": "true"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url=url, data=payload, auth=auth)
    print repo_name, response.status_code

def bzr_push():
    pass

def upload_git_repo():
    pass

def upload_bzr_repos():
    all_bzr_locations = subprocess.check_output(BZR_LOCATE, shell=True)
    for location in all_bzr_locations.split('\n'):
        print location
        # get all the git repo names 
        m = re.match(r'/labs/(\w+\d*)/bzr/([\w\d\-_]+)/', location)
        if m == None:
            continue
        lab_name = m.group(1)
        for repo_name in os.listdir(location):
            # form the bitbucket repo url
            bb_repo_name = (lab_name + "-" + repo_name).lower()
            repo_path = location + "/" + repo_name
            bb_repo_url = "%s%s.git" % (BB_URL, bb_repo_name)
            if repo_exists(bb_repo_url):
                print "Pushing to repo", bb_repo_name
                git_push(repo_path, bb_repo_name)
            else:
                print "Creating repo", bb_repo_name
                create_repo(bb_repo_name)
                print "Pushing to repo", bb_repo_name
                git_push(repo_path, bb_repo_name)


if __name__ == '__main__':
    upload_git_repos()