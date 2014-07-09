#!/usr/bin/env python
#----------------------------------------------------------
# odoo cli
#
# To install your odoo development environement type:
#
# wget -O- https://raw.githubusercontent.com/odoo/odoo/master/odoo.py | python
#
# The setup_* subcommands used to boostrap odoo are defined here inline and may
# only depends on the python 2.7 stdlib
#
# The rest of subcommands are defined in odoo/cli or in <module>/cli by
# subclassing the Command object
#
# https://raw.githubusercontent.com/odoo-dev/odoo/master-odoo-cmd-fme/odoo.py
#
#----------------------------------------------------------
import os
import re
import sys
import subprocess

GIT_HOOKS_PRE_PUSH = """
#!/usr/bin/env python2
import re
import sys
if re.search('github.com[:/]odoo/odoo.git$', sys.argv[2]):
    print "Pushing to /odoo/odoo.git is forbidden, please push to odoo-dev, use --no-verify to override"
    sys.exit(1)
"""

def printf(f,*l):
    print "odoo:" + f % l

def run(*l):
    if isinstance(l[0], list):
        l = l[0]
    printf("running %s", " ".join(l))
    subprocess.check_call(l)

def git_locate():
    # Locate git dir
    # TODO add support for os.environ.get('GIT_DIR')

    # check for an odoo child
    if os.path.isfile('odoo/.git/config'):
        os.chdir('odoo')

    path = os.getcwd()
    while path != '/':
        gitconfig_path = os.path.join(path, '.git/config')
        if os.path.isfile(gitconfig_path):
            release_py = os.path.join(path, 'openerp/release.py')
            if os.path.isfile(release_py):
                break
        path = os.path.dirname(path)
    if path == '/':
        path = None
    return path

def cmd_setup_git():
    git_dir = git_locate()
    if git_dir:
        printf('git repo found at %s',git_dir)
    else:
        run("git", "init", "odoo")
        os.chdir('odoo')
        git_dir = os.getcwd()
    if git_dir:
        # push sane config for git < 2.0, and hooks
        #run('git','config','push.default','simple')
        # alias
        run('git','config','alias.st','status')
        # merge bzr style
        run('git','config','merge.commit','no')
        # pull let me choose between merge or rebase only works in git > 2.0, use an alias for 1
        run('git','config','pull.ff','only')
        run('git','config','alias.pl','pull --ff-only')
        pre_push_path = os.path.join(git_dir, '.git/hooks/pre-push')
        open(pre_push_path,'w').write(GIT_HOOKS_PRE_PUSH.strip())
        os.chmod(pre_push_path, 0755)
        # setup odoo remote
        run('git','config','remote.odoo.url','https://github.com/odoo/odoo.git')
        run('git','config','remote.odoo.pushurl','git@github.com:odoo/odoo.git')
        run('git','config','--add','remote.odoo.fetch','dummy')
        run('git','config','--unset-all','remote.odoo.fetch')
        run('git','config','--add','remote.odoo.fetch','+refs/heads/*:refs/remotes/odoo/heads/*')
        # setup odoo-dev remote
        run('git','config','remote.odoo-dev.url','https://github.com/odoo-dev/odoo.git')
        run('git','config','remote.odoo-dev.pushurl','git@github.com:odoo-dev/odoo.git')
        run('git','remote','update')
        # setup master branch
        run('git','config','branch.master.remote','odoo')
        run('git','config','branch.master.merge','refs/heads/master')
        run('git','checkout','master')
    else:
        printf('no git repo found')

def cmd_setup_git_dev():
    git_dir = git_locate()
    if git_dir:
        # setup odoo-dev remote
        run('git','config','--add','remote.odoo-dev.fetch','dummy')
        run('git','config','--unset-all','remote.odoo-dev.fetch')
        run('git','config','--add','remote.odoo-dev.fetch','+refs/heads/*:refs/remotes/odoo-dev/heads/*')
        run('git','config','--add','remote.odoo-dev.fetch','+refs/pull/*:refs/remotes/odoo-dev/pull/*')
        run('git','remote','update')

def cmd_setup_git_review():
    git_dir = git_locate()
    if git_dir:
        # setup odoo-dev remote
        run('git','config','--add','remote.odoo.fetch','dummy')
        run('git','config','--unset-all','remote.odoo.fetch')
        run('git','config','--add','remote.odoo.fetch','+refs/heads/*:refs/remotes/odoo/heads/*')
        run('git','config','--add','remote.odoo.fetch','+refs/tags/*:refs/remotes/odoo/tags/*')
        run('git','config','--add','remote.odoo.fetch','+refs/pull/*:refs/remotes/odoo/pull/*')

def setup_deps_debian(git_dir):
    debian_control_path = os.path.join(git_dir, 'debian/control')
    debian_control = open(debian_control_path).read()
    debs = re.findall('python-[0-9a-z]+',debian_control)
    debs += ["postgresql"]
    proc = subprocess.Popen(['sudo','apt-get','install'] + debs, stdin=open('/dev/tty'))
    proc.communicate()

def cmd_setup_deps():
    git_dir = git_locate()
    if git_dir:
        if os.path.isfile('/etc/debian_version'):
            setup_deps_debian(git_dir)

def setup_pg_debian(git_dir):
    cmd = ['sudo','su','-','postgres','-c','createuser -s %s' % os.environ['USER']]
    subprocess.call(cmd)

def cmd_setup_pg():
    git_dir = git_locate()
    if git_dir:
        if os.path.isfile('/etc/debian_version'):
            setup_pg_debian(git_dir)

def cmd_setup():
    cmd_setup_git()
    cmd_setup_deps()
    cmd_setup_pg()

def main():
    # regsitry of commands
    g = globals()
    cmds = dict([(i[4:],g[i]) for i in g if i.startswith('cmd_')])
    # if curl URL | python2 then use command setup
    if len(sys.argv) == 1 and __file__ == '<stdin>':
        cmd_setup()
    elif len(sys.argv) == 2 and sys.argv[1] in cmds:
        cmds[sys.argv[1]]()
    else:
        import openerp
        openerp.cli.main()

if __name__ == "__main__":
    main()

