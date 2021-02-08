# Git hooks

This file hierarchy contains opt-in git hook shell scripts, they are script that
are automatically executed when performing some git actions like commiting or
pushing. The scripts can be used for various purposes like to automatically run
a code formatter on modified files just before it is commited.

The hierarchy works as follow, this root directory contains git hooks entry
scripts (`pre-push` and alike), every of those script execute the executable
files found in the corresponding `.d` subfolder (`pre-push.d` and alike). The
entry scripts should not be modified.

The `.githooks/scripts` folder contain various off-the-shelf sample scripts
written by the community. If you wish to reuse one of those files, simple copy
the script in one of the `.d` directory and edit it so it matches your system
environment.

## Install

To use this community-driven git hooks, you need to change your git config:

	$ git config core.hooksPath .githooks

You can then install any script in the directory corresponding to your hook.
Bellow an exemple to run pylint everytime you push your local branch to a remote
server:

	$ cp .githooks/scripts/pylint.sample .githooks/pre-push.d/pylint

You may edit the installed script so it matches your system environment.

## Contribute

You are free to contribute to the sample scripts just like the rest of the Odoo
source code. If your script requires external dependencies, make sure to
document where to find them and how to install them.
