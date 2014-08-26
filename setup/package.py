#!/usr/bin/env python2
import glob
import os
import optparse
import signal
import shutil
import socket
import subprocess
import time
import xmlrpclib

#----------------------------------------------------------
# Utils
#----------------------------------------------------------
join = os.path.join

def mkdir(d):
    if not os.path.isdir(d):
        os.makedirs(d)

def system(l,chdir=None):
    print l
    if chdir:
        cwd = os.getcwd()
        os.chdir(chdir)
    if isinstance(l,list):
        rc=os.spawnvp(os.P_WAIT, l[0], l)
    elif isinstance(l,str):
        tmp=['sh','-c',l]
        rc=os.spawnvp(os.P_WAIT, tmp[0], tmp)
    if chdir:
        os.chdir(cwd)
    return rc

#----------------------------------------------------------
# Stages
#----------------------------------------------------------

def rsync(o):
    pre = 'rsync -a --exclude .bzr --exclude .git --exclude *.pyc'
    cmd = pre.split(' ')
    system(cmd + ['%s/'%o.root, o.build])
    for i in glob.glob(join(o.build,'addons/*')):
        shutil.move(i, join(o.build,'openerp/addons'))
    for i in glob.glob(join(o.build,'setup/*')):
        shutil.move(i, join(o.build))
    open(join(o.build,'openerp','release.py'),'a').write('version = "%s-%s"\n'%(o.version,o.timestamp))

def publish_move(o,srcs,dest):
    for i in srcs:
        shutil.move(i,dest)
        # do the symlink
        bn = os.path.basename(i)
        latest = bn.replace(o.timestamp,'latest')
        latest_full = join(dest,latest)
        if bn != latest:
            if os.path.islink(latest_full):
                os.unlink(latest_full)
            os.symlink(bn,latest_full)

def sdist(o):
    cmd=['python2','setup.py', '--quiet', 'sdist']
    system(cmd,o.build)
    #l = glob.glob(join(o.pkg,'*%s*.tar.gz'%o.timestamp))
    #publish_move(o,l,join(o.pub,'src'))

def bdist_rpm(o):
    cmd=['python2','setup.py', '--quiet', 'bdist_rpm']
    system(cmd,o.build)
    #l = glob.glob(join(o.build,'dist/*%s-1*.rpm'%o.timestamp.replace('-','_')))
    #publish_move(o,l,join(o.pub,'rpm'))

def debian(o):
    cmd=['sed','-i','1s/^.*$/openerp (%s-%s-1) testing; urgency=low/'%(o.version,o.timestamp),'debian/changelog']
    system(cmd,o.build)
    cmd=['dpkg-buildpackage','-rfakeroot']
    system(cmd,o.build)

    #l = glob.glob(join(o.pkg,'*_*%s-1*'%o.timestamp))
    #publish_move(o,l,join(o.pub,'deb'))
    #system('dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz',join(o.pub,'deb'))

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
        l="kvm -net nic -net user,hostfwd=tcp:127.0.0.1:10022-:22,hostfwd=tcp:127.0.0.1:18069-:8069,hostfwd=tcp:127.0.0.1:15432-:5432 -drive".split(" ")
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

class KVMDebianTestTgz(KVM):
    def run(self):
        l = glob.glob(join(self.o.pkg,'*%s.tar.gz'%self.o.timestamp))
        self.rsync('%s openerp@127.0.0.1:src/'%l[0])
        script = """
            tar xzvf src/*.tar.gz
            cd openerp*
            sudo python setup.py install
            sudo su - postgres -c "createuser -s $USER"
            createdb t1
            openerp-server --stop-after-init -d t1 -i ` python -c "import os;print ','.join([i for i in os.listdir('openerp/addons') if i not in ['auth_openid','caldav','document_ftp','base_gengo', 'im', 'im_livechat'] and not i.startswith('hw_')]),;" `
        """
        self.ssh(script)
        self.ssh('nohup openerp-server >/dev/null 2>&1 &')
        time.sleep(5)
        l = xmlrpclib.ServerProxy('http://127.0.0.1:18069/xmlrpc/object').execute('t1',1,'admin','ir.module.module','search',[('state','=','installed')])
        i = len(l)
        if i >= 190:
            print "Tgz install: ",i," module installed"
        else:
            raise Exception("Tgz install failed only %s installed"%i)
        time.sleep(2)

class KVMDebianTestDeb(KVM):
    def run(self):
        l = glob.glob(join(self.o.pkg,'*%s*.deb'%self.o.timestamp))
        self.rsync('%s openerp@127.0.0.1:deb/'%l[0])
        script = """
            sudo dpkg -i deb/*
            sudo su - postgres -c "createuser -s $USER"
            createdb t1
            openerp-server --stop-after-init -d t1 -i base
        """
        #` python -c "import os;print ','.join([i for i in os.listdir('/usr/share/pyshared/openerp/addons') if i not in ['auth_openid','caldav','document_ftp', 'base_gengo'] and not i.startswith('hw_')]),;" `
        self.ssh(script)
        time.sleep(5)
        l = xmlrpclib.ServerProxy('http://127.0.0.1:18069/xmlrpc/object').execute('t1',1,'admin','ir.module.module','search',[('state','=','installed')])
        i = len(l)
        if i >= 1:
            print "Deb install: ",i," module installed"
        else:
            raise Exception("Tgz install failed only %s installed"%i)
        time.sleep(2)

class KVMWinBuildExe(KVM):
    def run(self):
        self.ssh("mkdir -p build")
        self.rsync('%s/ %s@127.0.0.1:build/server/' % (self.o.build, self.login))
        with open('windows/Makefile.version', 'w') as f:
            f.write("VERSION=%s\n" % self.o.version_full)
        with open('windows/Makefile.python', 'w') as f:
            f.write("PYTHON_VERSION=%s\n" % self.o.vm_win_python_version.replace('.', ''))
        self.rsync('windows/ %s@127.0.0.1:build/windows/' % self.login)
        self.rsync('windows/wkhtmltopdf/ %s@127.0.0.1:build/server/win32/wkhtmltopdf/' % self.login)
        self.ssh("cd build/windows;time make allinone;")
        self.rsync('%s@127.0.0.1:build/windows/files/ %s/' % (self.login, self.o.pkg), '')
        print "KVMWinBuildExe.run(): done"

class KVMWinTestExe(KVM):
    def run(self):
        setuppath = "%s/openerp-allinone-setup-%s.exe" % (self.o.pkg, self.o.version_full)
        setuplog = setuppath.replace('exe','log')
        self.rsync('"%s" %s@127.0.0.1:' % (setuppath, self.login))
        self.ssh("TEMP=/tmp ./openerp-allinone-setup-%s.exe /S" % self.o.version_full)
        self.ssh('ls /cygdrive/c/"Program Files"/"OpenERP %s"/' % self.o.version_full)
        self.rsync('"repo/lpopenerp_openobject-addons_7.0/" %s@127.0.0.1:/cygdrive/c/Program?Files/OpenERP?%s/Server/server/openerp/addons/' % (self.login, self.o.version_full), options='--exclude .bzrignore --exclude .bzr')
        self.ssh('ls /cygdrive/c/"Program Files"/"OpenERP %s"/Server/server/openerp/addons/' % self.o.version_full)

        self.ssh('PGPASSWORD=openpgpwd /cygdrive/c/"Program Files"/"OpenERP %s"/PostgreSQL/bin/createdb.exe -e -U openpg pack' % self.o.version_full)
        self.ssh('net stop "PostgreSQL_For_OpenERP"')
        self.ssh('net start "PostgreSQL_For_OpenERP"')
        self.ssh('mkdir test-reports')

        self.ssh('/cygdrive/c/"Program Files"/"OpenERP %s"/Server/server/openerp-server.exe -d pack -i base,report_webkit,product --stop-after-init --test-enable --log-level=test --test-report-directory=test-reports'%self.o.version_full)
        self.rsync('%s@127.0.0.1:/cygdrive/c/Program?Files/OpenERP?%s/Server/server/openerp-server.log "%s"' % (self.login, self.o.version_full, setuplog))
        self.rsync('%s@127.0.0.1:test-reports/ "%s"' % (self.login, self.o.pkg), options='')

#----------------------------------------------------------
# Options and Main
#----------------------------------------------------------

def options():
    op = optparse.OptionParser()
    timestamp = time.strftime("%Y%m%d-%H%M%S",time.gmtime())
    root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    build = "%s-%s" % (root, timestamp)

    op.add_option("-b", "--build", default=build, help="build directory (%default)", metavar="DIR")
    op.add_option("-p", "--pub", default=None, help="pub directory (%default)", metavar="DIR")
    op.add_option("-v", "--version", default='7.0', help="version (%default)")

    op.add_option("", "--vm-debian-image", default='/home/odoo/vm/debian6/debian6.vmdk', help="%default")
    op.add_option("", "--vm-debian-ssh-key", default='/home/odoo/vm/debian6/debian6_id_rsa', help="%default")
    op.add_option("", "--vm-debian-login", default='openerp', help="Debian login (%default)")

    op.add_option("", "--vm-winxp-image", default='/home/odoo/vm/winxp26/winxp26.vdi', help="%default")
    op.add_option("", "--vm-winxp-ssh-key", default='/home/odoo/vm/winxp26/id_rsa', help="%default")
    op.add_option("", "--vm-win-login", default='Naresh', help="Windows login (%default)")
    op.add_option("", "--vm-win-python-version", default='2.6', help="Windows Python version installed in the VM (default: %default)")

    op.add_option("", "--no-debian", action="store_true", help="don't build the debian package")
    op.add_option("", "--no-rpm", action="store_true", help="don't build the rpm package")
    op.add_option("", "--no-tarball", action="store_true", help="don't build the tarball")
    op.add_option("", "--no-windows", action="store_true", help="don't build the windows package")

    (o, args) = op.parse_args()
    # derive other options
    o.root = root
    o.timestamp = timestamp
    o.version_full = '%s-%s'%(o.version,o.timestamp)
    return o

def main():
    o = options()
    rsync(o)
    try:
        # tgz
        sdist(o)
        if os.path.isfile(o.vm_debian_image):
            KVMDebianTestTgz(o, o.vm_debian_image, o.vm_debian_ssh_key, o.vm_debian_login).start()

        # deb
        debian(o)
        if os.path.isfile(o.vm_debian_image):
            KVMDebianTestDeb(o, o.vm_debian_image, o.vm_debian_ssh_key, o.vm_debian_login).start()

        # exe
        if os.path.isfile(o.vm_winxp_image):
            KVMWinBuildExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_win_login).start()
            KVMWinTestExe(o, o.vm_winxp_image, o.vm_winxp_ssh_key, o.vm_win_login).start()
            l = glob.glob(join(o.pkg,'*all*%s*.exe'%o.timestamp))
            publish_move(o,l,join(o.pub,'exe'))

        # rpm
        bdist_rpm(o)

    finally:
        #shutil.rmtree(o.build)
        pass

if __name__ == '__main__':
    main()
