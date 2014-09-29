#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import optparse
import os
import pexpect
import shutil
import signal
import subprocess
import tempfile
import time
import xmlrpclib
from contextlib import contextmanager
from glob import glob
from os.path import abspath, dirname, join
from tempfile import NamedTemporaryFile


#----------------------------------------------------------
# Utils
#----------------------------------------------------------
execfile(join(dirname(__file__), '..', 'openerp', 'release.py'))
version = version.split('-')[0]

timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
PUBLISH_DIRS = {
    'tar.gz': 'src',
    'exe': 'exe',
    'deb': 'deb',
    'dsc': 'deb',
    'changes': 'deb',
    'deb.tar.gz': ['deb', 'tar.gz'],
    'noarch.rpm': 'rpm',
    'src.rpm': 'rpm',
}

def mkdir(d):
    if not os.path.isdir(d):
        os.makedirs(d)

def system(l, chdir=None):
    print l
    if chdir:
        cwd = os.getcwd()
        os.chdir(chdir)
    if isinstance(l, list):
        rc = os.spawnvp(os.P_WAIT, l[0], l)
    elif isinstance(l, str):
        tmp = ['sh', '-c', l]
        rc = os.spawnvp(os.P_WAIT, tmp[0], tmp)
    if chdir:
        os.chdir(cwd)
    return rc

def _rpc_count_modules(addr='http://127.0.0.1', port=8069, dbname='mycompany'):
    time.sleep(5)
    modules = xmlrpclib.ServerProxy('%s:%s/xmlrpc/object' % (addr, port)).execute(
        dbname, 1, 'admin', 'ir.module.module', 'search', [('state', '=', 'installed')]
    )
    if modules and len(modules) > 1:
        time.sleep(1)
        toinstallmodules = xmlrpclib.ServerProxy('%s:%s/xmlrpc/object' % (addr, port)).execute(
            dbname, 1, 'admin', 'ir.module.module', 'search', [('state', '=', 'to install')]
        )
        if toinstallmodules:
            print("Package test: FAILED. Not able to install dependencies of base.")
            raise Exception("Installation of package failed")
        else:
            print("Package test: successfuly installed %s modules" % len(modules))
    else:
        print("Package test: FAILED. Not able to install base.")
        raise Exception("Installation of package failed")

def publish(o, releases):
    def _publish(o, release):
        extension = ''.join(release.split('.', 1)[1])
        release_extension = PUBLISH_DIRS[extension][1] if isinstance(PUBLISH_DIRS[extension], list) else extension
        release_dir = PUBLISH_DIRS[extension][0] if isinstance(PUBLISH_DIRS[extension], list) else PUBLISH_DIRS[extension]

        release_filename = 'odoo_%s-%s.%s' % (version, timestamp, release_extension)
        release_path = join(o.pub, release_dir, release_filename)

        system('mkdir -p %s' % join(o.pub, release_dir))
        shutil.move(join(o.build_dir, release), release_path)

        if release_extension == 'deb':
            temp_path = tempfile.mkdtemp(suffix='debPackages')
            system(['cp', release_path, temp_path])
            with open(os.path.join(o.pub, 'deb', 'Packages'), 'w') as out:
                subprocess.call(['dpkg-scanpackages', '.'], stdout=out, cwd=temp_path)
            shutil.rmtree(temp_path)

        # Latest/symlink handler
        release_abspath = abspath(release_path)
        latest_abspath = release_abspath.replace(timestamp, 'latest')

        if os.path.islink(latest_abspath):
            os.unlink(latest_abspath)

        os.symlink(release_abspath, latest_abspath)

    if isinstance(releases, basestring):
        _publish(o, releases)
    elif isinstance(releases, list):
        for release in releases:
            _publish(o, release)

class OdooDocker(object):
    def __init__(self):
        self.log_file = NamedTemporaryFile(mode='w+b', prefix="bash", suffix=".txt", delete=False)
        self.port = 8069  # TODO sle: reliable way to get a free port?
        self.prompt_re = '(\r\nroot@|bash-).*# '
        self.timeout = 600

    def system(self, command):
        self.docker.sendline(command)
        self.docker.expect(self.prompt_re)

    def start(self, docker_image, build_dir, pub_dir):
        self.build_dir = build_dir
        self.pub_dir = pub_dir

        self.docker = pexpect.spawn(
            'docker run -v %s:/opt/release -p 127.0.0.1:%s:8069'
            ' -t -i %s /bin/bash --noediting' % (self.build_dir, self.port, docker_image),
            timeout=self.timeout
        )
        time.sleep(2)  # let the bash start
        self.docker.logfile_read = self.log_file
        self.id = subprocess.check_output('docker ps -l -q', shell=True)

    def end(self):
        try:
            _rpc_count_modules(port=str(self.port))
        except Exception, e:
            print('Exception during docker execution: %s:' % str(e))
            print('Error during docker execution: printing the bash output:')
            with open(self.log_file.name) as f:
                print '\n'.join(f.readlines())
            raise
        finally:
            self.docker.close()
            system('docker rm -f %s' % self.id)
            self.log_file.close()
            os.remove(self.log_file.name)

@contextmanager
def docker(docker_image, build_dir, pub_dir):
    _docker = OdooDocker()
    try:
        _docker.start(docker_image, build_dir, pub_dir)
        try:
            yield _docker
        except Exception, e:
            raise
    finally:
        _docker.end()

class KVM(object):
    def __init__(self, o, image, ssh_key='', login='openerp'):
        self.o = o
        self.image = image
        self.ssh_key = ssh_key
        self.login = login

    def timeout(self,signum,frame):
        print "vm timeout kill",self.pid
        os.kill(self.pid,15)

    def start(self):
        l="kvm -net nic,model=rtl8139 -net user,hostfwd=tcp:127.0.0.1:10022-:22,hostfwd=tcp:127.0.0.1:18069-:8069,hostfwd=tcp:127.0.0.1:15432-:5432 -drive".split(" ")
        #l.append('file=%s,if=virtio,index=0,boot=on,snapshot=on'%self.image)
        l.append('file=%s,snapshot=on'%self.image)
        #l.extend(['-vnc','127.0.0.1:1'])
        l.append('-nographic')
        print " ".join(l)
        self.pid=os.spawnvp(os.P_NOWAIT, l[0], l)
        time.sleep(10)
        signal.alarm(2400)
        signal.signal(signal.SIGALRM, self.timeout)
        try:
            self.run()
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            os.kill(self.pid,15)
            time.sleep(10)

    def ssh(self,cmd):
        l=['ssh','-o','UserKnownHostsFile=/dev/null','-o','StrictHostKeyChecking=no','-p','10022','-i',self.ssh_key,'%s@127.0.0.1'%self.login,cmd]
        system(l)

    def rsync(self,args,options='--delete --exclude .bzrignore'):
        cmd ='rsync -rt -e "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p 10022 -i %s" %s %s' % (self.ssh_key, options, args)
        system(cmd)

    def run(self):
        pass

class KVMWinBuildExe(KVM):
    def run(self):
        with open(join(self.o.build_dir, 'setup/win32/Makefile.version'), 'w') as f:
            f.write("VERSION=%s\n" % self.o.version_full)
        with open(join(self.o.build_dir, 'setup/win32/Makefile.python'), 'w') as f:
            f.write("PYTHON_VERSION=%s\n" % self.o.vm_winxp_python_version.replace('.', ''))

        self.ssh("mkdir -p build")
        self.rsync('%s/ %s@127.0.0.1:build/server/' % (self.o.build_dir, self.login))
        self.ssh("cd build/server/setup/win32;time make allinone;")
        self.rsync('%s@127.0.0.1:build/server/setup/win32/release/ %s/' % (self.login, self.o.build_dir), '')
        print "KVMWinBuildExe.run(): done"

class KVMWinTestExe(KVM):
    def run(self):
        # Cannot use o.version_full when the version is not correctly parsed
        # (for instance, containing *rc* or *dev*)
        setuppath = glob("%s/openerp-server-setup-*.exe" % self.o.build_dir)[0]
        setupfile = setuppath.split('/')[-1]
        setupversion = setupfile.split('openerp-server-setup-')[1].split('.exe')[0]

        self.rsync('"%s" %s@127.0.0.1:' % (setuppath, self.login))
        self.ssh("TEMP=/tmp ./%s /S" % setupfile)
        self.ssh('PGPASSWORD=openpgpwd /cygdrive/c/"Program Files"/"Odoo %s"/PostgreSQL/bin/createdb.exe -e -U openpg mycompany' % setupversion)
        self.ssh('/cygdrive/c/"Program Files"/"Odoo %s"/server/openerp-server.exe -d mycompany -i base --stop-after-init' % setupversion)
        self.ssh('net start odoo-server-8.0')
        _rpc_count_modules(port=18069)

#----------------------------------------------------------
# Stage: building
#----------------------------------------------------------
def _prepare_build_dir(o):
    cmd = ['rsync', '-a', '--exclude', '.git', '--exclude', '*.pyc', '--exclude', '*.pyo']
    system(cmd + ['%s/' % o.odoo_dir, o.build_dir])
    for i in glob(join(o.build_dir, 'addons/*')):
        shutil.move(i, join(o.build_dir, 'openerp/addons'))

def build_tgz(o):
    system(['python2', 'setup.py', '--quiet', 'sdist'], o.build_dir)
    system(['cp', glob('%s/dist/openerp-*.tar.gz' % o.build_dir)[0], '%s/odoo.tar.gz' % o.build_dir])

def build_deb(o):
    system(['dpkg-buildpackage', '-rfakeroot', '-uc', '-us'], o.build_dir)
    system(['cp', glob('%s/../odoo_*.deb' % o.build_dir)[0], '%s/odoo.deb' % o.build_dir])
    system(['cp', glob('%s/../odoo_*.dsc' % o.build_dir)[0], '%s/odoo.dsc' % o.build_dir])
    system(['cp', glob('%s/../odoo_*_amd64.changes' % o.build_dir)[0], '%s/odoo_amd64.changes' % o.build_dir])
    system(['cp', glob('%s/../odoo_*.tar.gz' % o.build_dir)[0], '%s/odoo.deb.tar.gz' % o.build_dir])

def build_rpm(o):
    system(['python2', 'setup.py', '--quiet', 'bdist_rpm'], o.build_dir)
    system(['cp', glob('%s/dist/openerp-*.noarch.rpm' % o.build_dir)[0], '%s/odoo.noarch.rpm' % o.build_dir])
    system(['cp', glob('%s/dist/openerp-*.src.rpm' % o.build_dir)[0], '%s/odoo.src.rpm' % o.build_dir])

def build_exe(o):
    KVMWinBuildExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_winxp_login).start()
    system(['cp', glob('%s/openerp*.exe' % o.build_dir)[0], '%s/odoo.exe' % o.build_dir])

#----------------------------------------------------------
# Stage: testing
#----------------------------------------------------------
def test_tgz(o):
    with docker('debian:stable', o.build_dir, o.pub) as wheezy:
        wheezy.release = 'odoo.tar.gz'
        wheezy.system('apt-get update -qq && apt-get upgrade -qq -y')
        wheezy.system("apt-get install postgresql python-dev postgresql-server-dev-all python-pip build-essential libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev libssl-dev libjpeg-dev -y")
        wheezy.system("service postgresql start")
        wheezy.system('su postgres -s /bin/bash -c "pg_dropcluster --stop 9.1 main"')
        wheezy.system('su postgres -s /bin/bash -c "pg_createcluster --start -e UTF-8 9.1 main"')
        wheezy.system('pip install -r /opt/release/requirements.txt')
        wheezy.system('/usr/local/bin/pip install /opt/release/%s' % wheezy.release)
        wheezy.system("useradd --system --no-create-home odoo")
        wheezy.system('su postgres -s /bin/bash -c "createuser -s odoo"')
        wheezy.system('su postgres -s /bin/bash -c "createdb mycompany"')
        wheezy.system('mkdir /var/lib/odoo')
        wheezy.system('chown odoo:odoo /var/lib/odoo')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py --addons-path=/usr/local/lib/python2.7/dist-packages/openerp/addons -d mycompany -i base --stop-after-init"')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py --addons-path=/usr/local/lib/python2.7/dist-packages/openerp/addons -d mycompany &"')

def test_deb(o):
    with docker('debian:stable', o.build_dir, o.pub) as wheezy:
        wheezy.release = 'odoo.deb'
        wheezy.system('/usr/bin/apt-get update -qq && /usr/bin/apt-get upgrade -qq -y')
        wheezy.system("apt-get install postgresql -y")
        wheezy.system("service postgresql start")
        wheezy.system('su postgres -s /bin/bash -c "pg_dropcluster --stop 9.1 main"')
        wheezy.system('su postgres -s /bin/bash -c "pg_createcluster --start -e UTF-8 9.1 main"')
        wheezy.system('su postgres -s /bin/bash -c "createdb mycompany"')
        wheezy.system('/usr/bin/dpkg -i /opt/release/%s' % wheezy.release)
        wheezy.system('/usr/bin/apt-get install -f -y')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py -c /etc/odoo/openerp-server.conf -d mycompany -i base --stop-after-init"')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py -c /etc/odoo/openerp-server.conf -d mycompany &"')

def test_rpm(o):
    with docker('centos:centos7', o.build_dir, o.pub) as centos7:
        centos7.release = 'odoo.noarch.rpm'
        centos7.system('rpm -Uvh http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-2.noarch.rpm')
        centos7.system('yum update -y && yum upgrade -y')
        centos7.system('yum install python-pip gcc python-devel -y')
        centos7.system('pip install pydot pyPdf vatnumber xlwt http://download.gna.org/pychart/PyChart-1.39.tar.gz')
        centos7.system('yum install postgresql postgresql-server postgresql-libs postgresql-contrib postgresql-devel -y')
        centos7.system('mkdir -p /var/lib/postgres/data')
        centos7.system('chown -R postgres:postgres /var/lib/postgres/data')
        centos7.system('chmod 0700 /var/lib/postgres/data')
        centos7.system('su postgres -c "initdb -D /var/lib/postgres/data -E UTF-8"')
        centos7.system('cp /usr/share/pgsql/postgresql.conf.sample /var/lib/postgres/data/postgresql.conf')
        centos7.system('su postgres -c "/usr/bin/pg_ctl -D /var/lib/postgres/data start"')
        centos7.system('su postgres -c "createdb mycompany"')
        centos7.system('export PYTHONPATH=${PYTHONPATH}:/usr/local/lib/python2.7/dist-packages')
        centos7.system('su postgres -c "createdb mycompany"')
        centos7.system('yum install /opt/release/%s -y' % centos7.release)
        centos7.system('su odoo -s /bin/bash -c "openerp-server -c /etc/odoo/openerp-server.conf -d mycompany -i base --stop-after-init"')
        centos7.system('su odoo -s /bin/bash -c "openerp-server -c /etc/odoo/openerp-server.conf -d mycompany &"')

def test_exe(o):
    KVMWinTestExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_winxp_login).start()

#----------------------------------------------------------
# Options and Main
#----------------------------------------------------------
def options():
    op = optparse.OptionParser()
    root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    build_dir = "%s-%s" % (root, timestamp)

    op.add_option("-b", "--build-dir", default=build_dir, help="build directory (%default)", metavar="DIR")
    op.add_option("-p", "--pub", default=None, help="pub directory (%default)", metavar="DIR")
    op.add_option("", "--no-testing", action="store_true", help="don't test the builded packages")
    op.add_option("-v", "--version", default='8.0', help="version (%default)")

    op.add_option("", "--no-debian", action="store_true", help="don't build the debian package")
    op.add_option("", "--no-rpm", action="store_true", help="don't build the rpm package")
    op.add_option("", "--no-tarball", action="store_true", help="don't build the tarball")
    op.add_option("", "--no-windows", action="store_true", help="don't build the windows package")

    # Windows VM
    op.add_option("", "--vm-winxp-image", default='/home/odoo/vm/winxp27/winxp27.vdi', help="%default")
    op.add_option("", "--vm-winxp-ssh-key", default='/home/odoo/vm/winxp27/id_rsa', help="%default")
    op.add_option("", "--vm-winxp-login", default='Naresh', help="Windows login (%default)")
    op.add_option("", "--vm-winxp-python-version", default='2.7', help="Windows Python version installed in the VM (default: %default)")

    (o, args) = op.parse_args()
    # derive other options
    o.odoo_dir = root
    o.pkg = join(o.build_dir, 'pkg')
    o.version_full = '%s-%s' % (o.version, timestamp)
    o.work = join(o.build_dir, 'openerp-%s' % o.version_full)
    o.work_addons = join(o.work, 'openerp', 'addons')
    return o

def main():
    o = options()
    _prepare_build_dir(o)
    try:
        if not o.no_tarball:
            build_tgz(o)
            if not o.no_testing:
                try:
                    test_tgz(o)
                    publish(o, 'odoo.tar.gz')
                except Exception, e:
                    print("Won't publish the tgz release.\n Exception: %s" % str(e))
        if not o.no_debian:
            build_deb(o)
            if not o.no_testing:
                try:
                    test_deb(o)
                    publish(o, ['odoo.deb', 'odoo.dsc', 'odoo_amd64.changes', 'odoo.deb.tar.gz'])
                except Exception, e:
                    print("Won't publish the deb release.\n Exception: %s" % str(e))
        if not o.no_rpm:
            build_rpm(o)
            if not o.no_testing:
                try:
                    test_rpm(o)
                    publish(o, ['odoo.noarch.rpm', 'odoo.src.rpm'])
                except Exception, e:
                    print("Won't publish the rpm release.\n Exception: %s" % str(e))
        if not o.no_windows:
            build_exe(o)
            if not o.no_testing:
                try:
                    test_exe(o)
                    publish(o, 'odoo.exe')
                except Exception, e:
                    print("Won't publish the exe release.\n Exception: %s" % str(e))
    except:
        pass
    finally:
        for leftover in glob('%s/../odoo_*' % o.build_dir):
            os.remove(leftover)

        shutil.rmtree(o.build_dir)
        print('Build dir %s removed' % o.build_dir)

        if not o.no_testing:
            system("docker rm -f `docker ps -a | awk '{print $1 }'` 2>>/dev/null")
            print('Remaining dockers removed')


if __name__ == '__main__':
    main()
