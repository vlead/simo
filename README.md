SIMO
====

Seamless syncing and mirroring bzr, svn and git repositories to a git server.  

Runs as a cron job and uploads all existing and new git, svn, bzr repos to bitbucket.


FEATURES
========

- Uploads git, bzr and svn repositories in that order
- Logs all stdout and stderr messages to simo.log
- Rotates the log file
- Sends email notification summarizing the run time and errors
