:orphan:

=============
Bazaar to git
=============

Initializing a working copy
---------------------------

Use the easy-setup shell script::

     curl -O https://raw.githubusercontent.com/odoo/odoo/master/odoo.py | python2

it will will ask a few questions and create a local copy.

Git concepts
------------

Remotes
~~~~~~~

Remotes are "remote repositories" which can be fetched from and pushed
to. Remotes can be listed with ``git remote``\ [#remote-default]_ and a local
repository can have any number of remotes. The setup script creates 2 remotes:

``odoo``
    the official repository and main branches, roughly corresponds to the old
    "mainline" branches in bazaar. You should never need to push to it, and by
    default your local copy is configured to forbid it.
``odoo-dev``
    a grab-bag of development branches, you can push your work to it so other
    coworkers can work with you.

Branches
~~~~~~~~

The working copy and each remote contain multiple branches. Local branches can
be listed by ``git branch``, remote branches can be listed with ``git branch
-r``. Both types can be listed with ``git branch -a``.

Work is only possible on local branches, even though it's possible to check
out a remote branch work on it will be lost.

Staging
~~~~~~~

``bzr commit`` takes all alterations to the working copy and creates a commit
from them. Git has an intermediate step called "staging". ``git commit`` will
create a commit from what has been staged, not from the working copy\
[#commit-no-staging]_. Staging is done with ``git add``. A commit with nothing
staged is a null operation.

.. warning::

    It's possible for a single file to have changes in both the index and
    working copy: if a file is altered, staged and altered again, the second
    set of change has to be staged separately

SHA1
~~~~

Git has no sequential identifier, each commit is uniquely identified by a SHA
(40 hexadecimal characters) roughly corresponding to a bazaar
revision-id. Providing the full sha is rarely necessary, any unique leading
substring is sufficient, e.g. ``dae86e`` will probably stand in for
``dae86e1950b1277e545cee180551750029cfe735``.

Basic development workflow
--------------------------

* update your remotes with ``git fetch --all``
* create your development branch with ``git checkout -b <branch_name>
  <source_branch>``. For instance if you wanted to add support for full-text
  search in master you could use ``git checkout -b master-fts-xxx odoo/master``
* do your changes, stage them with ``git add`` and commit them with ``git
  commit``
* if your branch is long-lived, you may want to update it to its parent

  - update the remotes with ``git fetch --all``
  - merge the remote branch into the local one with ``git merge --no-ff
    odoo/master``

* to push the branch to the development repository, use ``git push -u dev
  <branchname>``, this will automatically create a branch called
  ``<branchname>`` on dev. Next time around you do not have to use ``-u``
* once the feature is done, create a pull request

.. should we promote rebase? That would lead to cleaner histories, but if the
   branch is already pushed it requires force-pushing since the branch can't
   be fast-forwarded

.. git automatically creates a merge commit, should we configure merge with
   --no-commit?

.. make --no-ff the default in the config script?

.. warn about ``git pull``? It is ~ ``git fetch; git merge`` and should
   probably be avoided

.. CLI tools?

.. format for specifying issues? e.g. closes #42?

Tasks
-----

Converting your feature branches from bazaar
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`The readme`_ has some instructions.

Viewing history: ``git log``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``git log`` fulfills the same role as ``bzr log`` and is fairly similar, with
a few differences:

* ``git log`` has no ``-r`` argument, its first argument (optional) is a
  revision spec
* ``git log`` always operates on ranges, if a single commit is provided (via
  hash, tag, branch or other) it will list the specified commit *and all of
  its ancestors*. To see a single commit, use ``git show``.
* ``git log``'s second positional argument is a path (file or
  directory). Because both are optional, if both a revision and a file match
  the revision will be selected. It is recommended to use ``--`` before a file
  path::

    git log -- filepath

* ``git log`` will actually work if given a directory, instead of pegging the
  CPU forever
* ``git log`` works with removed files or directories without having to
  provide a revision during which the file or directory still existed
* ``git log`` has *lots* of options to customize the output, e.g. ``-p`` will
  display the changes to each file\ [#log-patch-empty]_, ``--name-status``
  will list the changed files and how they changed SVN-style (with a ``M`` or
  ``D`` prefix), ``--name-only`` will just list the changed files, ``--stat``
  generates a diffstat view, ``--grep`` filters by grepping on the commit
  message, …

Reverting uncommitted changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. danger:: Do *not* use ``git revert``, it does something completely
            different than ``bzr revert``

* If you have altered files which you want to revert, use ``git checkout --
  <path>``. To revert every file in the directory, use ``git checkout -- .``
* If you have staged a file and you want to unstage it, use ``git reset HEAD
  <file>``. This will not revert the file's changes, the file will be marked
  as modified again

Diffing: ``git diff``
~~~~~~~~~~~~~~~~~~~~~

``git diff`` is fairly similar to ``bzr diff``: it compares the working copy
with stored content and can be restricted to a given file path. However:

* ``git diff`` compares the working copy and the staging area, not the latest
  commit
* ``git diff --staged`` compares the staging area and the latest commit
* ``git diff HEAD`` ignores the staging area and compares the working copy
  with the latest commit. More generally ``git diff <commit>`` will diff the
  working copy and the specified commit
* to diff between commits, simply pass the commit identifiers (no ``-r``
  argument)
* ``git diff --stat`` provides a diffstat-view of the diff, and can be
  combined with other flags. It can be used as an intermediate between ``git
  status`` and ``git status -s``

Update to a previous revision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``git checkout`` takes an arbitrary commit, the equivalent to ``bzr update
-r<rev>`` is thus ``git checkout <rev>``.

File from the past
~~~~~~~~~~~~~~~~~~

``bzr cat -r<revision> <filename>`` shows the file ``<filename>`` as it was at
``<revision>``. The Git equivalent is ``git show <revision>:<filename>``

Incorrect last commit: fix it
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the last commit has to be fixed a bit (error, missing data,
incomplete/incorrect commit message) it can be fixed with ``git commit
--amend``. Instead of creating a new commit, it adds whatever is being
committed to the previous commit.

Incorrect last commit: remove it
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the last commit has to be removed entirely (similar to ``bzr uncommit``),
use ``git reset HEAD~1``.

.. danger:: do not use this command or the previous one on commits you have
            already pushed

Useful tips
-----------

Partial operations
~~~~~~~~~~~~~~~~~~

``checkout``, ``add``, ``commit``, ``reset`` and ``stash`` can take a ``-p``
flag, which allows operating (staging, reverting, ...) on a subset of the
file. It opens a UI allowing the selection (or not) of each patch hunk, and
even the splitting of hunk if they're too big.

Allows reverting only part of the changes to a file, or cleanly splitting
refactorings and fixes mixed in a file.

short status
~~~~~~~~~~~~

The default ``status`` command is very verbose (though useful, it provides
instructions for reverting things). The ``-s`` flag provides an SVN-like
display instead with just a listing of files and :abbr:`A (Added)`, :abbr:`M
(Modified)` or :abbr:`D (Deleted)` flags next to them. Each file can have 2
flags, the first is for the index (difference between the last commit and the
index) and the and the second is for the working copy (difference between the
index and the working copy).

``checkout`` shortcut
~~~~~~~~~~~~~~~~~~~~~

``checkout -`` will behave like ``cd -``, it will switch to the previously
checked-out branch/commit

.. [#remote-default] by default, ``git remote`` will only give the names of
                     the various remotes. ``git remote -v`` will give the name
                     and URL of each remote.

.. [#commit-no-staging] the ``-a`` option will automatically stage modified
                        and deleted files

.. [#log-patch-empty] but only the changes performed by this actual commit,
                      for a merge the merged changes are not considered part
                      of the merge commit

.. _the readme: https://github.com/odoo/odoo/blob/master/README.md#migration-from-bazaar
