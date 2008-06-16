##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
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
###############################################################################

import tarfile
import re
import urllib2
import os
import shutil
import tools


# remove an existing version of modules if it exist
def remove(name):
	adp = tools.config['addons_path']
	addons = os.listdir(adp)
	if name in addons:
		try:
			shutil.rmtree(os.path.join(adp, name))
		except:
			print "Unable to remove module %s !" % name

def install(name, url):
	tar = tarfile.open(mode="r|gz", fileobj=urllib2.urlopen(url))
	for tarinfo in tar:
		tar.extract(tarinfo, tools.config['addons_path'])

def upgrade():
	import pooler
	cr = pooler.db.cursor()

	toinit = []
	toupdate = []

#	print 'Check for correct rights (create and unlink on addons)...'
	# todo: touch addons/test.txt
	# todo: rm addons/test.txt

	print 'Check for modules to remove...'
	cr.execute('select id,name,url from ir_module_module where state=%s', ('to remove',))
	for module_id,name,url in cr.fetchall():
		print '\tremoving module %s' % name
		remove(name)
		cr.execute('update ir_module_module set state=%s where id=%d', ('uninstalled', module_id))
		cr.commit()

	print 'Check for modules to upgrade...'
	cr.execute('select id,name,url from ir_module_module where state=%s', ('to upgrade',))
	for module_id,name,url in cr.fetchall():
		print '\tupgrading module %s' % name
		remove(name)
		install(name, url)
		cr.execute('update ir_module_module set state=%s where id=%d', ('installed', module_id))
		cr.commit()
		toupdate.append(name)

	print 'Check for modules to install...'
	cr.execute('select id,name,url from ir_module_module where state=%s', ('to install',))
	for module_id,name,url in cr.fetchall():
		print '\tinstalling module %s' % name
		install(name, url)
		cr.execute('update ir_module_module set state=%s where id=%d', ('installed', module_id))
		cr.commit()
		toinit.append(name)

	print 'Initializing all datas...'

	cr.commit()
	cr.close()
	return (toinit, toupdate)

