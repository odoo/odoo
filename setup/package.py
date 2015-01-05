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
from sys import stdout
from tempfile import NamedTemporaryFile


#----------------------------------------------------------
# Utils
#----------------------------------------------------------
execfile(join(dirname(__file__), '..', 'openerp', 'release.py'))
version = version.split('-')[0]
timestamp = time.strftime("%Y%m%d", time.gmtime())
GPGPASSPHRASE = os.getenv('GPGPASSPHRASE')
GPGID = os.getenv('GPGID')
PUBLISH_DIRS = {
    'debian': 'deb',
    'redhat': 'rpm',
    'tarball': 'src',
    'windows': 'exe',
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

def publish(o, type, extensions):
    def _publish(o, release):
        arch = ''
        filename = release.split(os.path.sep)[-1]

        release_dir = PUBLISH_DIRS[type]
        release_path = join(o.pub, release_dir, filename)

        system('mkdir -p %s' % join(o.pub, release_dir))
        shutil.move(join(o.build_dir, release), release_path)

        # Latest/symlink handler
        release_abspath = abspath(release_path)
        latest_abspath = release_abspath.replace(timestamp, 'latest')

        if os.path.islink(latest_abspath):
            os.unlink(latest_abspath)

        os.symlink(release_abspath, latest_abspath)

        return release_path

    published = []
    for extension in extensions:
        release = glob("%s/odoo_*.%s" % (o.build_dir, extension))[0]
        published.append(_publish(o, release))
    return published

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
    system(['python2', 'setup.py', 'sdist', '--quiet', '--formats=gztar,zip'], o.build_dir)
    system(['mv', glob('%s/dist/odoo-*.tar.gz' % o.build_dir)[0], '%s/odoo_%s.%s.tar.gz' % (o.build_dir, version, timestamp)])
    system(['mv', glob('%s/dist/odoo-*.zip' % o.build_dir)[0], '%s/odoo_%s.%s.zip' % (o.build_dir, version, timestamp)])

def build_deb(o):
    # Append timestamp to version for the .dsc to refer the right .tar.gz
    cmd=['sed', '-i', '1s/^.*$/odoo (%s.%s) stable; urgency=low/'%(version,timestamp), 'debian/changelog']
    subprocess.call(cmd, cwd=o.build_dir)
    deb = pexpect.spawn('dpkg-buildpackage -rfakeroot -k%s' % GPGID, cwd=o.build_dir)
    deb.logfile = stdout
    deb.expect_exact('Enter passphrase: ', timeout=1200)
    deb.send(GPGPASSPHRASE + '\r\n')
    deb.expect_exact('Enter passphrase: ')
    deb.send(GPGPASSPHRASE + '\r\n')
    deb.expect(pexpect.EOF)
    system(['mv', glob('%s/../odoo_*.deb' % o.build_dir)[0], '%s' % o.build_dir])
    system(['mv', glob('%s/../odoo_*.dsc' % o.build_dir)[0], '%s' % o.build_dir])
    system(['mv', glob('%s/../odoo_*_amd64.changes' % o.build_dir)[0], '%s' % o.build_dir])
    system(['mv', glob('%s/../odoo_*.tar.gz' % o.build_dir)[0], '%s' % o.build_dir])

def build_rpm(o):
    system(['python2', 'setup.py', '--quiet', 'bdist_rpm'], o.build_dir)
    system(['mv', glob('%s/dist/odoo-*.noarch.rpm' % o.build_dir)[0], '%s/odoo_%s.%s.noarch.rpm' % (o.build_dir, version, timestamp)])

def build_exe(o):
    KVMWinBuildExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_winxp_login).start()
    system(['cp', glob('%s/openerp*.exe' % o.build_dir)[0], '%s/odoo_%s.%s.exe' % (o.build_dir, version, timestamp)])

#----------------------------------------------------------
# Stage: testing
#----------------------------------------------------------
def _prepare_testing(o):
    if not o.no_tarball or not o.no_debian:
        subprocess.call(["mkdir", "docker_debian"], cwd=o.build_dir)
        subprocess.call(["cp", "package.dfdebian", os.path.join(o.build_dir, "docker_debian", "Dockerfile")],
                        cwd=os.path.join(o.odoo_dir, "setup"))
        # Use rsync to copy requirements.txt in order to keep original permissions
        subprocess.call(["rsync", "-a", "requirements.txt", os.path.join(o.build_dir, "docker_debian")],
                        cwd=os.path.join(o.odoo_dir))
        subprocess.call(["docker", "build", "-t", "odoo-debian-nightly-tests", "."],
                        cwd=os.path.join(o.build_dir, "docker_debian"))
    if not o.no_rpm:
        subprocess.call(["mkdir", "docker_centos"], cwd=o.build_dir)
        subprocess.call(["cp", "package.dfcentos", os.path.join(o.build_dir, "docker_centos", "Dockerfile")],
                        cwd=os.path.join(o.odoo_dir, "setup"))
        subprocess.call(["docker", "build", "-t", "odoo-centos-nightly-tests", "."],
                        cwd=os.path.join(o.build_dir, "docker_centos"))

def test_tgz(o):
    with docker('odoo-debian-nightly-tests', o.build_dir, o.pub) as wheezy:
        wheezy.release = '*.tar.gz'
        wheezy.system("service postgresql start")
        wheezy.system('/usr/local/bin/pip install /opt/release/%s' % wheezy.release)
        wheezy.system("useradd --system --no-create-home odoo")
        wheezy.system('su postgres -s /bin/bash -c "createuser -s odoo"')
        wheezy.system('su postgres -s /bin/bash -c "createdb mycompany"')
        wheezy.system('mkdir /var/lib/odoo')
        wheezy.system('chown odoo:odoo /var/lib/odoo')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py --addons-path=/usr/local/lib/python2.7/dist-packages/openerp/addons -d mycompany -i base --stop-after-init"')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py --addons-path=/usr/local/lib/python2.7/dist-packages/openerp/addons -d mycompany &"')

def test_deb(o):
    with docker('odoo-debian-nightly-tests', o.build_dir, o.pub) as wheezy:
        wheezy.release = '*.deb'
        wheezy.system("service postgresql start")
        wheezy.system('su postgres -s /bin/bash -c "createdb mycompany"')
        wheezy.system('/usr/bin/dpkg -i /opt/release/%s' % wheezy.release)
        wheezy.system('/usr/bin/apt-get install -f -y')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py -c /etc/odoo/openerp-server.conf -d mycompany -i base --stop-after-init"')
        wheezy.system('su odoo -s /bin/bash -c "odoo.py -c /etc/odoo/openerp-server.conf -d mycompany &"')

def test_rpm(o):
    with docker('odoo-centos-nightly-tests', o.build_dir, o.pub) as centos7:
        centos7.release = '*.noarch.rpm'
        # Start postgresql
        centos7.system('su postgres -c "/usr/bin/pg_ctl -D /var/lib/postgres/data start"')
        centos7.system('sleep 5')
        centos7.system('su postgres -c "createdb mycompany"')
        # Odoo install
        centos7.system('yum install -d 0 -e 0 /opt/release/%s -y' % centos7.release)
        centos7.system('su odoo -s /bin/bash -c "openerp-server -c /etc/odoo/openerp-server.conf -d mycompany -i base --stop-after-init"')
        centos7.system('su odoo -s /bin/bash -c "openerp-server -c /etc/odoo/openerp-server.conf -d mycompany &"')

def test_exe(o):
    KVMWinTestExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_winxp_login).start()

#---------------------------------------------------------
# Generates Packages, Sources and Release files of debian package
#---------------------------------------------------------
def gen_deb_package(o, published_files):
    # Executes command to produce file_name in path, and moves it to o.pub/deb
    def _gen_file(o, (command, file_name), path):
        cur_tmp_file_path = os.path.join(path, file_name)
        with open(cur_tmp_file_path, 'w') as out:
            subprocess.call(command, stdout=out, cwd=path)
        system(['cp', cur_tmp_file_path, os.path.join(o.pub, 'deb', file_name)])

    # Copy files to a temp directory (required because the working directory must contain only the
    # files of the last release)
    temp_path = tempfile.mkdtemp(suffix='debPackages')
    for pub_file_path in published_files:
        system(['cp', pub_file_path, temp_path])

    commands = [
        (['dpkg-scanpackages', '.'], "Packages"),  # Generate Packages file
        (['dpkg-scansources', '.'], "Sources"),  # Generate Sources file
        (['apt-ftparchive', 'release', '.'], "Release")  # Generate Release file
    ]
    # Generate files
    for command in commands:
        _gen_file(o, command, temp_path)
    # Remove temp directory
    shutil.rmtree(temp_path)

    # Generate Release.gpg (= signed Release)
    # Options -abs: -a (Create ASCII armored output), -b (Make a detach signature), -s (Make a signature)
    subprocess.call(['gpg', '--default-key', GPGID, '--passphrase', GPGPASSPHRASE, '--yes', '-abs', '--no-tty', '-o', 'Release.gpg', 'Release'], cwd=os.path.join(o.pub, 'deb'))

#---------------------------------------------------------
# Generates an RPM repo
#---------------------------------------------------------
def gen_rpm_repo(o, file_name):
    # Sign the RPM
    rpmsign = pexpect.spawn('/bin/bash', ['-c', 'rpm --resign %s' % file_name], cwd=os.path.join(o.pub, 'rpm'))
    rpmsign.expect_exact('Enter pass phrase: ')
    rpmsign.send(GPGPASSPHRASE + '\r\n')
    rpmsign.expect(pexpect.EOF)

    # Removes the old repodata
    subprocess.call(['rm', '-rf', os.path.join(o.pub, 'rpm', 'repodata')])

    # Copy files to a temp directory (required because the working directory must contain only the
    # files of the last release)
    temp_path = tempfile.mkdtemp(suffix='rpmPackages')
    subprocess.call(['cp', file_name, temp_path])

    subprocess.call(['createrepo', temp_path])  # creates a repodata folder in temp_path
    subprocess.call(['cp', '-r', os.path.join(temp_path, "repodata"), os.path.join(o.pub, 'rpm')])

    # Remove temp directory
    shutil.rmtree(temp_path)

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
    if not o.no_testing:
        _prepare_testing(o)
    try:
        if not o.no_tarball:
            build_tgz(o)
            try:
                if not o.no_testing:
                    test_tgz(o)
                published_files = publish(o, 'tarball', ['tar.gz', 'zip'])
            except Exception, e:
                print("Won't publish the tgz release.\n Exception: %s" % str(e))
        if not o.no_debian:
            build_deb(o)
            try:
                if not o.no_testing:
                    test_deb(o)
                published_files = publish(o, 'debian', ['deb', 'dsc', 'changes', 'tar.gz'])
                gen_deb_package(o, published_files)
            except Exception, e:
                print("Won't publish the deb release.\n Exception: %s" % str(e))
        if not o.no_rpm:
            build_rpm(o)
            try:
                if not o.no_testing:
                    test_rpm(o)
                published_files = publish(o, 'redhat', ['noarch.rpm'])
                gen_rpm_repo(o, published_files[0])
            except Exception, e:
                print("Won't publish the rpm release.\n Exception: %s" % str(e))
        if not o.no_windows:
            build_exe(o)
            try:
                if not o.no_testing:
                    test_exe(o)
                published_files = publish(o, 'windows', ['exe'])
            except Exception, e:
                print("Won't publish the exe release.\n Exception: %s" % str(e))
    except:
        pass
    finally:
        shutil.rmtree(o.build_dir)
        print('Build dir %s removed' % o.build_dir)

        if not o.no_testing:
            system("docker rm -f `docker ps -a | awk '{print $1 }'` 2>>/dev/null")
            print('Remaining dockers removed')


if __name__ == '__main__':
    main()
