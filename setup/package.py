#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import print_function
import logging
import optparse
import os
import pexpect
import shutil
import signal
import subprocess
import tempfile
import time
import traceback
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib
from contextlib import contextmanager
from glob import glob
from os.path import abspath, dirname, join
from sys import stdout, stderr
from tempfile import NamedTemporaryFile

# apt-get install rsync python-pexpect debhelper python-setuptools

#----------------------------------------------------------
# Utils
#----------------------------------------------------------
exec(open(join(dirname(__file__), '..', 'odoo', 'release.py'), 'rb').read())
version = version.split('-')[0].replace('saas~','')
docker_version = version.replace('+', '')
timestamp = time.strftime("%Y%m%d", time.gmtime())
GPGPASSPHRASE = os.getenv('GPGPASSPHRASE')
GPGID = os.getenv('GPGID')
PUBLISH_DIRS = {
    'debian': 'deb',
    'redhat': 'rpm',
    'tarball': 'src',
    'windows': 'exe',
}
ADDONS_NOT_TO_PUBLISH = [
]


def move_glob(source, wildcards, destination):
    """Move files matched by wildcards from source to destination
    wildcards can be a single string wildcard like '*.deb' or a list of wildcards
    """
    if not os.path.isdir(destination):
        raise BaseException('Destination "{}" is not a directory'.format(destination))
    if isinstance(wildcards, str):
        wildcards = [wildcards]
    for wc in wildcards:
        for file_path in glob(os.path.join(source, wc)):
            shutil.move(file_path, destination)

def mkdir(d):
    if not os.path.isdir(d):
        os.makedirs(d)

def system(l, chdir=None):
    logging.info("System call: {}".format(l))
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
            logging.error("Package test: FAILED. Not able to install dependencies of base.")
            raise Exception("Installation of package failed")
        else:
            logging.info("Package test: successfuly installed %s modules" % len(modules))
    else:
        logging.error("Package test: FAILED. Not able to install base.")
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
        release = glob("%s/odoo_*.%s" % (o.build_dir, extension))
        if release:
            published.append(_publish(o, release[0]))
    return published

class OdooDocker(object):
    def __init__(self):
        self.log_file = NamedTemporaryFile(mode='w+b', prefix="bash", suffix=".txt", delete=False)
        self.port = 8069  # TODO sle: reliable way to get a free port?
        self.prompt_re = '[root@nightly-tests] # '
        self.timeout = 600

    def system(self, command):
        self.docker.sendline(command)
        self.docker.expect_exact(self.prompt_re)

    def start(self, docker_image, build_dir, pub_dir):
        self.build_dir = build_dir
        self.pub_dir = pub_dir

        self.docker = pexpect.spawn(
            'docker run -v %s:/opt/release -p 127.0.0.1:%s:8069'
            ' -t -i %s /bin/bash --noediting' % (self.build_dir, self.port, docker_image),
            timeout=self.timeout,
            searchwindowsize=len(self.prompt_re) + 1,
        )
        time.sleep(2)  # let the bash start
        self.docker.logfile_read = self.log_file
        self.id = subprocess.check_output('docker ps -l -q', shell=True).strip().decode('ascii')

    def end(self):
        try:
            _rpc_count_modules(port=str(self.port))
        except Exception as e:
            logging.error('Exception during docker execution: %s:' % str(e))
            logging.error('Error during docker execution: printing the bash output:')
            with open(self.log_file.name) as f:
                print('\n'.join(f.readlines()), file=stderr)
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
        except Exception:
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
        logging.warning("vm timeout kill",self.pid)
        os.kill(self.pid,15)

    def start(self):
        l="kvm -cpu core2duo -smp 2,sockets=2,cores=1,threads=1 -net nic,model=rtl8139 -net user,hostfwd=tcp:127.0.0.1:10022-:22,hostfwd=tcp:127.0.0.1:18069-:8069,hostfwd=tcp:127.0.0.1:15432-:5432 -m 1024 -drive".split(" ")
        #l.append('file=%s,if=virtio,index=0,boot=on,snapshot=on'%self.image)
        l.append('file=%s,snapshot=on'%self.image)
        #l.extend(['-vnc','127.0.0.1:1'])
        l.append('-nographic')
        logging.info("Starting kvm: {}".format( " ".join(l)))
        self.pid=os.spawnvp(os.P_NOWAIT, l[0], l)
        time.sleep(50)
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

    def rsync(self,args,options='--delete --exclude .git --exclude .tx --exclude __pycache__'):
        cmd ='rsync -rt -e "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p 10022 -i %s" %s %s' % (self.ssh_key, options, args)
        system(cmd)

    def run(self):
        pass

class KVMWinBuildExe(KVM):
    def run(self):
        with open(join(self.o.build_dir, 'setup/win32/Makefile.version'), 'w') as f:
            f.write("VERSION=%s\n" % version.replace('~', '_').replace('+', ''))
        with open(join(self.o.build_dir, 'setup/win32/Makefile.python'), 'w') as f:
            f.write("PYTHON_VERSION=%s\n" % self.o.vm_winxp_python_version.replace('.', ''))
        with open(join(self.o.build_dir, 'setup/win32/Makefile.servicename'), 'w') as f:
            f.write("SERVICENAME=%s\n" % nt_service_name)

        remote_build_dir = '/cygdrive/c/odoobuild/server/'

        self.ssh("mkdir -p build")
        logging.info("Syncing Odoo files to virtual machine...")
        self.rsync('%s/ %s@127.0.0.1:%s' % (self.o.build_dir, self.login, remote_build_dir))
        self.ssh("cd {}setup/win32;time make allinone;".format(remote_build_dir))
        self.rsync('%s@127.0.0.1:%ssetup/win32/release/ %s/' % (self.login, remote_build_dir, self.o.build_dir), '')
        logging.info("KVMWinBuildExe.run(): done")

class KVMWinTestExe(KVM):
    def run(self):
        setuppath = glob("%s/openerp-server-setup-*.exe" % self.o.build_dir)[0]
        setupfile = setuppath.split('/')[-1]
        setupversion = setupfile.split('openerp-server-setup-')[1].split('.exe')[0]

        self.rsync('"%s" %s@127.0.0.1:' % (setuppath, self.login))
        self.ssh("TEMP=/tmp ./%s /S" % setupfile)
        self.ssh('PGPASSWORD=openpgpwd /cygdrive/c/"Program Files"/"Odoo %s"/PostgreSQL/bin/createdb.exe -e -U openpg mycompany' % setupversion)
        self.ssh('netsh advfirewall set publicprofile state off')
        self.ssh('/cygdrive/c/"Program Files"/"Odoo {sv}"/python/python.exe \'c:\\Program Files\\Odoo {sv}\\server\\odoo-bin\' -d mycompany -i base --stop-after-init'.format(sv=setupversion))
        _rpc_count_modules(port=18069)

#----------------------------------------------------------
# Stage: building
#----------------------------------------------------------
def _prepare_build_dir(o, win32=False):
    
    cmd = ['rsync', '-a', '--exclude', '.git', '--exclude', '*.pyc', '--exclude', '*.pyo']
    if not win32:
        cmd += ['--exclude', 'setup/win32']
    system(cmd + ['%s/' % o.odoo_dir, o.build_dir])
    for addon_path in glob(join(o.build_dir, 'addons/*')):
        if addon_path.split(os.path.sep)[-1] not in ADDONS_NOT_TO_PUBLISH:
            try:
                shutil.move(addon_path, join(o.build_dir, 'odoo/addons'))
            except shutil.Error as e:
                # Thrown when the add-on is already in odoo/addons (if _prepare_build_dir
                # has already been called once)
                logging.warning("Warning '{}' while moving addon '{}'".format(e,addon_path))
                if addon_path.startswith(o.build_dir) and os.path.isdir(addon_path):
                    logging.info("Removing '{}'".format(addon_path))
                    try:
                        shutil.rmtree(addon_path)
                    except shutil.Error as rm_error:
                        logging.warning("Cannot remove '{}': {}".format(addon_path, rm_error))

def build_tgz(o):
    system(['python3', 'setup.py', 'sdist', '--quiet', '--formats=gztar,zip'], o.build_dir)
    system(['mv', glob('%s/dist/odoo-*.tar.gz' % o.build_dir)[0], '%s/odoo_%s.%s.tar.gz' % (o.build_dir, version, timestamp)])
    system(['mv', glob('%s/dist/odoo-*.zip' % o.build_dir)[0], '%s/odoo_%s.%s.zip' % (o.build_dir, version, timestamp)])

def build_deb(o):
    # Append timestamp to version for the .dsc to refer the right .tar.gz
    cmd=['sed', '-i', '1s/^.*$/odoo (%s.%s) stable; urgency=low/'%(version,timestamp), 'debian/changelog']
    subprocess.call(cmd, cwd=o.build_dir)
    if not o.no_debsign:
        deb = pexpect.spawn('dpkg-buildpackage -rfakeroot -k%s' % GPGID, cwd=o.build_dir)
        deb.logfile = stdout.buffer
        if GPGPASSPHRASE:
            deb.expect_exact('Enter passphrase: ', timeout=1200)
            deb.send(GPGPASSPHRASE + '\r\n')
            deb.expect_exact('Enter passphrase: ')
            deb.send(GPGPASSPHRASE + '\r\n')
        deb.expect(pexpect.EOF, timeout=1200)
    else:
        subprocess.call(['dpkg-buildpackage', '-rfakeroot', '-uc', '-us'], cwd=o.build_dir)
    # As the packages are built in the parent of the buildir, we move them back to build_dir
    build_dir_parent = '{}/../'.format(o.build_dir)
    wildcards = ['odoo_{}'.format(wc) for wc in ('*.deb', '*.dsc', '*_amd64.changes', '*.tar.gz', '*.tar.xz')]
    move_glob(build_dir_parent, wildcards, o.build_dir)

def build_rpm(o):
    system(['python3', 'setup.py', '--quiet', 'bdist_rpm'], o.build_dir)
    system(['mv', glob('%s/dist/odoo-*.noarch.rpm' % o.build_dir)[0], '%s/odoo_%s.%s.noarch.rpm' % (o.build_dir, version, timestamp)])

def build_exe(o):
    KVMWinBuildExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_winxp_login).start()
    system(['cp', glob('%s/openerp*.exe' % o.build_dir)[0], '%s/odoo_%s.%s.exe' % (o.build_dir, version, timestamp)])

#----------------------------------------------------------
# Stage: testing
#----------------------------------------------------------
def _prepare_testing(o):
    logging.info('Preparing testing')
    if not o.no_tarball:
        logging.info('Preparing docker container instance for tarball')
        subprocess.call(["mkdir", "docker_src"], cwd=o.build_dir)
        subprocess.call(["cp", "package.dfsrc", os.path.join(o.build_dir, "docker_src", "Dockerfile")],
                        cwd=os.path.join(o.odoo_dir, "setup"))
        # Use rsync to copy requirements.txt in order to keep original permissions
        subprocess.call(["rsync", "-a", "requirements.txt", os.path.join(o.build_dir, "docker_src")],
                        cwd=os.path.join(o.odoo_dir))
        subprocess.call(["docker", "build", "-t", "odoo-%s-src-nightly-tests" % docker_version, "."],
                        cwd=os.path.join(o.build_dir, "docker_src"))
    if not o.no_debian:
        logging.info('Preparing docker container instance for debian')
        subprocess.call(["mkdir", "docker_debian"], cwd=o.build_dir)
        subprocess.call(["cp", "package.dfdebian", os.path.join(o.build_dir, "docker_debian", "Dockerfile")],
                        cwd=os.path.join(o.odoo_dir, "setup"))
        # Use rsync to copy requirements.txt in order to keep original permissions
        subprocess.call(["rsync", "-a", "requirements.txt", os.path.join(o.build_dir, "docker_debian")],
                        cwd=os.path.join(o.odoo_dir))
        subprocess.call(["docker", "build", "-t", "odoo-%s-debian-nightly-tests" % docker_version, "."],
                        cwd=os.path.join(o.build_dir, "docker_debian"))
    if not o.no_rpm:
        logging.info('Preparing docker container instance for RPM') 
        subprocess.call(["mkdir", "docker_fedora"], cwd=o.build_dir)
        subprocess.call(["cp", "package.dffedora", os.path.join(o.build_dir, "docker_fedora", "Dockerfile")],
                        cwd=os.path.join(o.odoo_dir, "setup"))
        subprocess.call(["docker", "build", "-t", "odoo-%s-fedora-nightly-tests" % docker_version, "."],
                        cwd=os.path.join(o.build_dir, "docker_fedora"))

def test_tgz(o):
    logging.info('Testing tarball in docker')
    with docker('odoo-%s-src-nightly-tests' % docker_version, o.build_dir, o.pub) as wheezy:
        wheezy.release = '*.tar.gz'
        wheezy.system("service postgresql start")
        wheezy.system('pip3 install /opt/release/%s' % wheezy.release)
        wheezy.system("useradd --system --no-create-home odoo")
        wheezy.system('su postgres -s /bin/bash -c "createuser -s odoo"')
        wheezy.system('su postgres -s /bin/bash -c "createdb mycompany"')
        wheezy.system('mkdir /var/lib/odoo')
        wheezy.system('chown odoo:odoo /var/lib/odoo')
        wheezy.system('su odoo -s /bin/bash -c "odoo -d mycompany -i base --stop-after-init"')
        wheezy.system('su odoo -s /bin/bash -c "odoo -d mycompany &"')

def test_deb(o):
    logging.info('Testing deb package in docker')
    with docker('odoo-%s-debian-nightly-tests' % docker_version, o.build_dir, o.pub) as wheezy:
        wheezy.release = '*.deb'
        wheezy.system("service postgresql start")
        wheezy.system('su postgres -s /bin/bash -c "createdb mycompany"')
        wheezy.system('/usr/bin/dpkg -i /opt/release/%s' % wheezy.release)
        wheezy.system('/usr/bin/apt-get install -f -y')
        wheezy.system('su odoo -s /bin/bash -c "odoo -c /etc/odoo/odoo.conf -d mycompany -i base --stop-after-init"')
        wheezy.system('su odoo -s /bin/bash -c "odoo -c /etc/odoo/odoo.conf -d mycompany &"')

def test_rpm(o):
    logging.info('Testing rpm in docker')
    with docker('odoo-%s-fedora-nightly-tests' % docker_version, o.build_dir, o.pub) as fedora24:
        fedora24.release = '*.noarch.rpm'
        # Start postgresql
        fedora24.system('su postgres -c "/usr/bin/pg_ctl -D /var/lib/postgres/data start"')
        fedora24.system('sleep 5')
        fedora24.system('su postgres -c "createdb mycompany"')
        # Odoo install
        fedora24.system('dnf install -d 0 -e 0 /opt/release/%s -y' % fedora24.release)
        fedora24.system('su odoo -s /bin/bash -c "odoo -c /etc/odoo/odoo.conf -d mycompany -i base --stop-after-init"')
        fedora24.system('su odoo -s /bin/bash -c "odoo -c /etc/odoo/odoo.conf -d mycompany &"')

def test_exe(o):
    logging.info('Testng windows installer in KVM')
    KVMWinTestExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_winxp_login).start()

#---------------------------------------------------------
# Generates Packages, Sources and Release files of debian package
#---------------------------------------------------------
def gen_deb_package(o, published_files):
    # Executes command to produce file_name in path, and moves it to o.pub/deb
    def _gen_file(o, command, file_name, path):
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
        _gen_file(o, command[0], command[-1], temp_path)
    # Remove temp directory
    shutil.rmtree(temp_path)

    if not o.no_debsign:
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

    log_levels = { "debug" : logging.DEBUG, "info": logging.INFO, "warning": logging.WARN, "error": logging.ERROR, "critical": logging.CRITICAL }

    op.add_option("-b", "--build-dir", default=build_dir, help="build directory (%default)", metavar="DIR")
    op.add_option("-p", "--pub", default=None, help="pub directory (%default)", metavar="DIR")
    op.add_option("", "--no-testing", action="store_true", help="don't test the built packages")

    op.add_option("", "--no-debian", action="store_true", help="don't build the debian package")
    op.add_option("", "--no-debsign", action="store_true", help="don't sign the debian package")
    op.add_option("", "--no-rpm", action="store_true", help="don't build the rpm package")
    op.add_option("", "--no-tarball", action="store_true", help="don't build the tarball")
    op.add_option("", "--no-windows", action="store_true", help="don't build the windows package")

    # Windows VM
    op.add_option("", "--vm-winxp-image", default='/home/odoo/vm/win1036/win10_winpy36.qcow2', help="%default")
    op.add_option("", "--vm-winxp-ssh-key", default='/home/odoo/vm/win1036/id_rsa', help="%default")
    op.add_option("", "--vm-winxp-login", default='Naresh', help="Windows login (%default)")
    op.add_option("", "--vm-winxp-python-version", default='3.6', help="Windows Python version installed in the VM (default: %default)")
    
    op.add_option("", "--no-remove", action="store_true", help="don't remove build dir")
    op.add_option("", "--logging", action="store", type="choice", choices=list(log_levels.keys()), default="info", help="Logging level")

    (o, args) = op.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %I:%M:%S', level=log_levels[o.logging])
    # derive other options
    o.odoo_dir = root
    o.pkg = join(o.build_dir, 'pkg')
    o.work = join(o.build_dir, 'openerp-%s' % version)
    o.work_addons = join(o.work, 'odoo', 'addons')

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
            except Exception as e:
                logging.error("Won't publish the tgz release.\n Exception: %s" % str(e))
        if not o.no_debian:
            build_deb(o)
            try:
                if not o.no_testing:
                    test_deb(o)
                published_files = publish(o, 'debian', ['deb', 'dsc', 'changes', 'tar.xz'])
                gen_deb_package(o, published_files)
            except Exception as e:
                logging.error("Won't publish the deb release.\n Exception: %s" % str(e))
                traceback.print_exc()
        if not o.no_rpm:
            build_rpm(o)
            try:
                if not o.no_testing:
                    test_rpm(o)
                published_files = publish(o, 'redhat', ['noarch.rpm'])
                gen_rpm_repo(o, published_files[0])
            except Exception as e:
                logging.error("Won't publish the rpm release.\n Exception: %s" % str(e))
        if not o.no_windows:
            _prepare_build_dir(o, win32=True)
            build_exe(o)
            try:
                if not o.no_testing:
                    test_exe(o)
                published_files = publish(o, 'windows', ['exe'])
            except Exception as e:
                logging.error("Won't publish the exe release.\n Exception: %s" % str(e))
    except Exception as e:
        logging.error('Something bad happened ! : {}'.format(e))
        traceback.print_exc()
    finally:
        if o.no_remove:
            logging.info('Build dir "{}" not removed'.format(o.build_dir))
        else:
            shutil.rmtree(o.build_dir)
            logging.info('Build dir %s removed' % o.build_dir)

        if not o.no_testing and not (o.no_debian and o.no_rpm and o.no_tarball):
            system("docker rm -f `docker ps -a | awk '{print $1 }'` 2>>/dev/null")
            logging.info('Remaining dockers removed')


if __name__ == '__main__':
    main()
