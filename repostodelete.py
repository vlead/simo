"""
This script identifies repositories that are no longer listed on the developer 
portal but exist on the sources virtual server.

Get the list of git repos from sources container
Get the list of git repos from developer portal (mysql db)
Diff gives the repos that are no longer listed on the developer portal, hence
can be removed.

Repeat for svn and bzr repos.
"""

import MySQLdb
import subprocess
import re
import os

TRASH = "corrupt-repos/"
PATH = "/labs/"
GIT_LOCATE = r"find %s -maxdepth 3 -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "git")
BZR_LOCATE = r"find %s -maxdepth 5 -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "trunk")
SVN_LOCATE = r"find %s -maxdepth 3 -name %s -exec du -sh {} \; | grep -v '^4.0K' | cut -f2" % (PATH, "svn")
LAB_ID_REGEX = r"\w+\d*"


def get_portal_repo_names():
    print "get_portal_repo_names.begin"
    db = MySQLdb.connect("localhost", "", "", "redmine_dump")
    cursor = db.cursor()
    cursor.execute("SELECT lab_id, reponame, repotype from repos")
    repo_list = cursor.fetchall()
    print "get_portal_repo_names.end"
    return set(repo_list)

def get_git_repos():
    git_repos = set()
    all_git_locations = subprocess.check_output(GIT_LOCATE, shell=True)
    for location in all_git_locations.split('\n'):
        m = re.match("/labs/(%s)/" % LAB_ID_REGEX, location)
        if m == None:
            continue
        lab_id = m.group(1)
        for repo_name in os.listdir(location):
            git_repos.add((lab_id, repo_name, 'git'))
    return git_repos

def get_svn_repos():
    svn_repos = set()
    all_svn_locations = subprocess.check_output(SVN_LOCATE, shell=True)
    for location in all_svn_locations.split('\n'):
        m = re.match("/labs/(%s)/svn" % LAB_ID_REGEX, location)
        if m == None:
            continue
        lab_id = m.group(1)
        for repo_name in os.listdir(location):
            svn_repos.add((lab_id, repo_name, 'svn'))
    return svn_repos

def get_bzr_repos():
    bzr_repos = set()
    all_bzr_locations = subprocess.check_output(BZR_LOCATE, shell=True)
    for location in all_bzr_locations.split('\n'):
        m = re.match(r'/labs/(\w+\d*)/bzr/([\w\d\-_]+)/', location)
        if m == None:
            continue
        lab_id = m.group(1)
        repo_name = m.group(2)
        bzr_repos.add((lab_id, repo_name, 'bzr'))
    return bzr_repos

def get_container_repo_names():
    return get_git_repos().union(get_svn_repos().union(get_bzr_repos()))

def delete_repo(lab_id, repo_name, repo_type):
    repo_path = PATH + lab_id + "/" + repo_type + "/" + repo_name
    subprocess.check_call("mv %s %s" % (repo_path, TRASH+lab_id+"-"+repo_name), shell=True)

def main():
    repos_to_delete = get_container_repo_names() - get_portal_repo_names()
    print repos_to_delete
    for record in repos_to_delete:
        print "Deleting %s %s %s " % record
        delete_repo(*record)


if __name__ == '__main__':
    main()

