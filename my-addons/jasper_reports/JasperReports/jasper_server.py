# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2019-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import os
import glob
import time
import socket
import subprocess
from xmlrpc import client as xmlrpclib
import logging

from odoo.exceptions import UserError
from odoo.tools.translate import _


class JasperServer:

    def __init__(self, port=8090):
        self.port = port
        self.pidfile = None
        self.javapath = None
        url = 'http://localhost:%d' % port
        self.proxy = xmlrpclib.ServerProxy(url, allow_none=True)
        self.logger = logging.getLogger(__name__)

    def error(self, message):
        if self.logger:
            self.logger.error("%s" % message)

    def path(self):
        return os.path.abspath(os.path.dirname(__file__))

    def start(self):
        java_path = self.javapath
        if java_path is False:
            raise UserError(_('Java Path Not Found !\n'
                              'Please add java path into the jasper '
                              'configuration page under the company form '
                              'view'))
        else:
            libraries = str(java_path) + '/lib'
            if os.path.exists(str(libraries)):
                self.javapath = java_path
            else:
                raise UserError(_('libraries Not Found !\n'
                                  'No libraries found in Java'))

        env = {}
        env.update(os.environ)
        if os.name == 'nt':
            a = ';'
        else:
            a = ':'
        libs = os.path.join(self.path(), '..', 'java', 'lib', '*.jar')
        env['CLASSPATH'] = os.path.join(self.path(), '..', 'java' + a) + \
            a.join(glob.glob(libs)) + a + os.path.join(
                self.path(), '..', 'custom_reports')

        cwd = os.path.join(self.path(), '..', 'java')

        # Set headless = True because otherwise, java may use
        # existing X session and if session is closed JasperServer
        # would start throwing exceptions. So we better avoid
        # using the session at all.
        command = ['java', '-Djava.awt.headless=true',
                   '-XX:MaxHeapSize=512m',
                   '-XX:InitialHeapSize=512m',
                   '-XX:CompressedClassSpaceSize=64m',
                   '-XX:MaxMetaspaceSize=128m',
                   '-XX:+UseConcMarkSweepGC',
                   'com.nantic.jasperreports.JasperServer',
                   str(self.port)]
        process = subprocess.Popen(command, env=env, cwd=cwd)

        if self.pidfile:
            with open(self.pidfile, 'w') as f:
                f.write(str(process.pid))

    def execute(self, *args):
        """
        Render report and return the number of pages generated.
        """
        try:
            return self.proxy.Report.execute(*args)
        except socket.error as e:
            self.start()
            for x in range(40):
                time.sleep(1)
                try:
                    return self.proxy.Report.execute(*args)
                except socket.error as e:
                    self.error("EXCEPTION: %s %s" % (str(e), str(e.args)))
                    pass
                except xmlrpclib.Fault as e:
                    raise UserError(_('Report Error\n%s') % e)
        except xmlrpclib.Fault as e:
            raise UserError(_('Report Error\n%s') % e)
