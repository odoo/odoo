# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
#
##############################################################################

import tarfile
import re
import urllib
import os
import tools
from osv import fields, osv, orm
import zipfile
import release
import zipimport

import wizard
import addons
import pooler
import netsvc

ver_regexp = re.compile("^(\\d+)((\\.\\d+)*)([a-z]?)((_(pre|p|beta|alpha|rc)\\d*)*)(-r(\\d+))?$")
suffix_regexp = re.compile("^(alpha|beta|rc|pre|p)(\\d*)$")

def vercmp(ver1, ver2):
    """
    Compare two versions
    Take from portage_versions.py
    @param ver1: version to compare with
    @type ver1: string (example "1.2-r3")
    @param ver2: version to compare again
    @type ver2: string (example "2.1-r1")
    @rtype: None or float
    @return:
    1. position if ver1 is greater than ver2
    2. negative if ver1 is less than ver2
    3. 0 if ver1 equals ver2
    4. None if ver1 or ver2 are invalid
    """

    match1 = ver_regexp.match(ver1)
    match2 = ver_regexp.match(ver2)

    if not match1 or not match1.groups():
        return None
    if not match2 or not match2.groups():
        return None

    list1 = [int(match1.group(1))]
    list2 = [int(match2.group(1))]

    if len(match1.group(2)) or len(match2.group(2)):
        vlist1 = match1.group(2)[1:].split(".")
        vlist2 = match2.group(2)[1:].split(".")
        for i in range(0, max(len(vlist1), len(vlist2))):
            # Implicit .0 is given -1, so 1.0.0 > 1.0
            # would be ambiguous if two versions that aren't literally equal
            # are given the same value (in sorting, for example).
            if len(vlist1) <= i or len(vlist1[i]) == 0:
                list1.append(-1)
                list2.append(int(vlist2[i]))
            elif len(vlist2) <= i or len(vlist2[i]) == 0:
                list1.append(int(vlist1[i]))
                list2.append(-1)
            # Let's make life easy and use integers unless we're forced to use floats
            elif (vlist1[i][0] != "0" and vlist2[i][0] != "0"):
                list1.append(int(vlist1[i]))
                list2.append(int(vlist2[i]))
            # now we have to use floats so 1.02 compares correctly against 1.1
            else:
                list1.append(float("0."+vlist1[i]))
                list2.append(float("0."+vlist2[i]))
    # and now the final letter
    if len(match1.group(4)):
        list1.append(ord(match1.group(4)))
    if len(match2.group(4)):
        list2.append(ord(match2.group(4)))

    for i in range(0, max(len(list1), len(list2))):
        if len(list1) <= i:
            return -1
        elif len(list2) <= i:
            return 1
        elif list1[i] != list2[i]:
            return list1[i] - list2[i]

    # main version is equal, so now compare the _suffix part
    list1 = match1.group(5).split("_")[1:]
    list2 = match2.group(5).split("_")[1:]

    for i in range(0, max(len(list1), len(list2))):
        # Implicit _p0 is given a value of -1, so that 1 < 1_p0
        if len(list1) <= i:
            s1 = ("p","-1")
        else:
            s1 = suffix_regexp.match(list1[i]).groups()
        if len(list2) <= i:
            s2 = ("p","-1")
        else:
            s2 = suffix_regexp.match(list2[i]).groups()
        if s1[0] != s2[0]:
            return suffix_value[s1[0]] - suffix_value[s2[0]]
        if s1[1] != s2[1]:
            # it's possible that the s(1|2)[1] == ''
            # in such a case, fudge it.
            try:
                r1 = int(s1[1])
            except ValueError:
                r1 = 0
            try:
                r2 = int(s2[1])
            except ValueError:
                r2 = 0
            if r1 - r2:
                return r1 - r2

    # the suffix part is equal to, so finally check the revision
    if match1.group(9):
        r1 = int(match1.group(9))
    else:
        r1 = 0
    if match2.group(9):
        r2 = int(match2.group(9))
    else:
        r2 = 0
    return r1 - r2


class module_repository(osv.osv):
    _name = "ir.module.repository"
    _description = "Module Repository"
    _columns = {
        'name': fields.char('Name', size=128),
        'url': fields.char('Url', size=256, required=True),
        'sequence': fields.integer('Sequence', required=True),
        'filter': fields.char('Filter', size=128, required=True,
            help='Regexp to search module on the repository webpage:\n'
            '- The first parenthesis must match the name of the module.\n'
            '- The second parenthesis must match all the version number.\n'
            '- The last parenthesis must match the extension of the module.'),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'sequence': lambda *a: 5,
        'filter': lambda *a: 'href="([a-zA-Z0-9_]+)-('+release.version.rsplit('.', 1)[0]+'.(\\d+)((\\.\\d+)*)([a-z]?)((_(pre|p|beta|alpha|rc)\\d*)*)(-r(\\d+))?)(\.zip)"',
        'active': lambda *a: 1,
    }
    _order = "sequence"
module_repository()

class module_category(osv.osv):
    _name = "ir.module.category"
    _description = "Module Category"

    def _module_nbr(self,cr,uid, ids, prop, unknow_none,context):
        cr.execute('select category_id,count(*) from ir_module_module where category_id in ('+','.join(map(str,ids))+') or category_id in (select id from ir_module_category where parent_id in ('+','.join(map(str,ids))+')) group by category_id')
        result = dict(cr.fetchall())
        for id in ids:
            cr.execute('select id from ir_module_category where parent_id=%d', (id,))
            childs = [c for c, in cr.fetchall()]
            result[id] = reduce(lambda x,y:x+y, [result.get(c, 0) for c in childs], result.get(id, 0))
        return result

    _columns = {
        'name': fields.char("Name", size=128, required=True),
        'parent_id': fields.many2one('ir.module.category', 'Parent Category', select=True),
        'child_ids': fields.one2many('ir.module.category', 'parent_id', 'Parent Category'),
        'module_nr': fields.function(_module_nbr, method=True, string='# of Modules', type='integer')
    }
    _order = 'name'
module_category()

class module(osv.osv):
    _name = "ir.module.module"
    _description = "Module"

    def get_module_info(self, name):
        try:
            f = tools.file_open(os.path.join(name, '__terp__.py'))
            data = f.read()
            info = eval(data)
            if 'version' in info:
                info['version'] = release.version.rsplit('.', 1)[0] + '.' + info['version']
            f.close()
        except:
            return {}
        return info

    def _get_installed_version(self, cr, uid, ids, field_name=None, arg=None, context={}):
        res = {}
        for m in self.browse(cr, uid, ids):
            if m.state in ('installed', 'to upgrade', 'to remove'):
                res[m.id] = self.get_module_info(m.name).get('version', '')
            else:
                res[m.id] = ''
        return res

    _columns = {
        'name': fields.char("Name", size=128, readonly=True, required=True),
        'category_id': fields.many2one('ir.module.category', 'Category', readonly=True),
        'shortdesc': fields.char('Short description', size=256, readonly=True),
        'description': fields.text("Description", readonly=True),
        'author': fields.char("Author", size=128, readonly=True),
        'website': fields.char("Website", size=256, readonly=True),
        'installed_version': fields.function(_get_installed_version, method=True,
            string='Installed version', type='char'),
        'latest_version': fields.char('Latest version', size=64, readonly=True),
        'published_version': fields.char('Published Version', size=64, readonly=True),
        'url': fields.char('URL', size=128),
        'dependencies_id': fields.one2many('ir.module.module.dependency',
            'module_id', 'Dependencies', readonly=True),
        'state': fields.selection([
            ('uninstallable','Not Installable'),
            ('uninstalled','Not Installed'),
            ('installed','Installed'),
            ('to upgrade','To be upgraded'),
            ('to remove','To be removed'),
            ('to install','To be installed')
        ], string='State', readonly=True),
        'demo': fields.boolean('Demo data'),
        'license': fields.selection([('GPL-2', 'GPL-2'),
            ('Other proprietary', 'Other proprietary')], string='License',
            readonly=True),
    }

    _defaults = {
        'state': lambda *a: 'uninstalled',
        'demo': lambda *a: False,
        'license': lambda *a: 'GPL-2',
    }
    _order = 'name'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the module must be unique !')
    ]

    def unlink(self, cr, uid, ids, context=None):
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        for mod in self.read(cr, uid, ids, ['state'], context):
            if mod['state'] in ('installed', 'to upgrade', 'to remove', 'to install'):
                raise orm.except_orm(_('Error'),
                        _('You try to remove a module that is installed or will be installed'))
        return super(module, self).unlink(cr, uid, ids, context=context)
    
    def state_update(self, cr, uid, ids, newstate, states_to_update, context={}, level=50):
        if level<1:
            raise orm.except_orm(_('Error'), _('Recursion error in modules dependencies !'))
        demo = False
        for module in self.browse(cr, uid, ids):
            mdemo = False
            go_deeper = False
            for dep in module.dependencies_id:
                if dep.state == 'unknown':
                    raise orm.except_orm(_('Error'), _('You try to install a module that depends on the module: %s.\nBut this module is not available in your system.') % (dep.name,))
                if dep.state != newstate:
                    go_deeper = True
                    ids2 = self.search(cr, uid, [('name','=',dep.name)])
                    mdemo = self.state_update(cr, uid, ids2, newstate, states_to_update, context, level-1,) or mdemo
            if not go_deeper:
                mdemo = module.demo
            if module.state in states_to_update:
                self.write(cr, uid, [module.id], {'state': newstate, 'demo':mdemo})
            demo = demo or mdemo
        return demo

    def button_install(self, cr, uid, ids, context={}):
        return self.state_update(cr, uid, ids, 'to install', ['uninstalled'], context)

    def button_install_cancel(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'uninstalled', 'demo':False})
        return True

    def button_uninstall(self, cr, uid, ids, context={}):
        for module in self.browse(cr, uid, ids):
            cr.execute('''select m.state,m.name
                from
                    ir_module_module_dependency d
                join
                    ir_module_module m on (d.module_id=m.id)
                where
                    d.name=%s and
                    m.state not in ('uninstalled','uninstallable','to remove')''', (module.name,))
            res = cr.fetchall()
            if res:
                raise orm.except_orm(_('Error'), _('The module you are trying to remove depends on installed modules :\n %s') % '\n'.join(map(lambda x: '\t%s: %s' % (x[0], x[1]), res)))
        self.write(cr, uid, ids, {'state': 'to remove'})
        return True

    def button_uninstall_cancel(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'installed'})
        return True
    def button_upgrade(self, cr, uid, ids, context=None):
        return self.state_update(cr, uid, ids, 'to upgrade', ['installed'], context)
    def button_upgrade_cancel(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'installed'})
        return True
    def button_update_translations(self, cr, uid, ids, context=None):
        self.update_translations(cr, uid, ids)
        return True

    # update the list of available packages
    def update_list(self, cr, uid, context={}):
        robj = self.pool.get('ir.module.repository')
        res = [0, 0] # [update, add]

        # iterate through installed modules and mark them as being so
        for name in addons.get_modules():
            mod_name = name
            if name[-4:]=='.zip':
                mod_name=name[:-4]
            ids = self.search(cr, uid, [('name','=',mod_name)])
            if ids:
                id = ids[0]
                mod = self.browse(cr, uid, id)
                terp = self.get_module_info(mod_name)
                if terp.get('installable', True) and mod.state == 'uninstallable':
                    self.write(cr, uid, id, {'state': 'uninstalled'})
                if vercmp(terp.get('version', ''), mod.latest_version or '0') > 0:
                    self.write(cr, uid, id, {
                        'latest_version': terp.get('version'),
                        'url': ''})
                    res[0] += 1
                self.write(cr, uid, id, {
                    'description': terp.get('description', ''),
                    'shortdesc': terp.get('name', ''),
                    'author': terp.get('author', 'Unknown'),
                    'website': terp.get('website', ''),
                    'license': terp.get('license', 'GPL-2'),
                    })
                cr.execute('DELETE FROM ir_module_module_dependency\
                        WHERE module_id = %d', (id,))
                self._update_dependencies(cr, uid, ids[0], terp.get('depends',
                    []))
                self._update_category(cr, uid, ids[0], terp.get('category',
                    'Uncategorized'))
                continue
            terp_file = addons.get_module_resource(name, '__terp__.py')
            mod_path = addons.get_module_path(name)
            if os.path.isdir(mod_path) or os.path.islink(mod_path) or zipfile.is_zipfile(mod_path):
                terp = self.get_module_info(mod_name)
                if not terp or not terp.get('installable', True):
                    continue
                if not os.path.isfile(mod_path+'.zip'):
                    import imp
                    # XXX must restrict to only addons paths
                    imp.load_module(name, *imp.find_module(mod_name))
                else:
                    import zipimport
                    zimp = zipimport.zipimporter(mod_path+'.zip')
                    zimp.load_module(mod_name)
                id = self.create(cr, uid, {
                    'name': mod_name,
                    'state': 'uninstalled',
                    'description': terp.get('description', ''),
                    'shortdesc': terp.get('name', ''),
                    'author': terp.get('author', 'Unknown'),
                    'website': terp.get('website', ''),
                    'latest_version': terp.get('version', ''),
                    'license': terp.get('license', 'GPL-2'),
                })
                res[1] += 1
                self._update_dependencies(cr, uid, id, terp.get('depends', []))
                self._update_category(cr, uid, id, terp.get('category', 'Uncategorized'))

        import socket
        socket.setdefaulttimeout(10)
        for repository in robj.browse(cr, uid, robj.search(cr, uid, [])):
            try:
                index_page = urllib.urlopen(repository.url).read()
            except IOError, e:
                if e.errno == 21:
                    raise orm.except_orm(_('Error'),
                            _("This url '%s' must provide an html file with links to zip modules") % (repository.url))
                else:
                    raise
            modules = re.findall(repository.filter, index_page, re.I+re.M)
            mod_sort = {}
            for m in modules:
                name = m[0]
                version = m[1]
                extension = m[-1]
                if version == 'x': # 'x' version was a mistake
                    version = '0'
                if name in mod_sort:
                    if vercmp(version, mod_sort[name][0]) <= 0:
                        continue
                mod_sort[name] = [version, extension]
            for name in mod_sort.keys():
                version, extension = mod_sort[name]
                url = repository.url+'/'+name+'-'+version+extension
                ids = self.search(cr, uid, [('name','=',name)])
                if not ids:
                    self.create(cr, uid, {
                        'name': name,
                        'latest_version': version,
                        'published_version': version,
                        'url': url,
                        'state': 'uninstalled',
                    })
                    res[1] += 1
                else:
                    id = ids[0]
                    latest_version = self.read(cr, uid, id, ['latest_version'])\
                            ['latest_version']
                    if latest_version == 'x': # 'x' version was a mistake
                        latest_version = '0'
                    c = vercmp(version, latest_version)
                    if c > 0:
                        self.write(cr, uid, id,
                                {'latest_version': version, 'url': url})
                        res[0] += 1
                    published_version = self.read(cr, uid, id, ['published_version'])\
                            ['published_version']
                    if published_version == 'x' or not published_version:
                        published_version = '0'
                    c = vercmp(version, published_version)
                    if c > 0:
                        self.write(cr, uid, id,
                                {'published_version': version})
        return res

    def download(self, cr, uid, ids, download=True, context=None):
        res = []
        for mod in self.browse(cr, uid, ids, context=context):
            if not mod.url:
                continue
            match = re.search('-([a-zA-Z0-9\._-]+)(\.zip)', mod.url, re.I)
            version = '0'
            if match:
                version = match.group(1)            
            if vercmp(mod.installed_version or '0', version) >= 0:
                continue
            res.append(mod.url)
            if not download:
                continue
            zipfile = urllib.urlopen(mod.url).read()
            fname = addons.get_module_path(mod.name+'.zip')            
            try:
                fp = file(fname, 'wb')
                fp.write(zipfile)
                fp.close()
            except IOError, e:
                raise orm.except_orm(_('Error'), _('Can not create the module file:\n %s') % (fname,))
            terp = self.get_module_info(mod.name)
            self.write(cr, uid, mod.id, {
                'description': terp.get('description', ''),
                'shortdesc': terp.get('name', ''),
                'author': terp.get('author', 'Unknown'),
                'website': terp.get('website', ''),
                'license': terp.get('license', 'GPL-2'),
                })
            cr.execute('DELETE FROM ir_module_module_dependency ' \
                    'WHERE module_id = %d', (mod.id,))
            self._update_dependencies(cr, uid, mod.id, terp.get('depends',
                []))
            self._update_category(cr, uid, mod.id, terp.get('category',
                'Uncategorized'))
            # Import module
            zimp = zipimport.zipimporter(fname)
            zimp.load_module(mod.name)
        return res

    def _update_dependencies(self, cr, uid, id, depends=[]):
        for d in depends:
            cr.execute('INSERT INTO ir_module_module_dependency (module_id, name) values (%d, %s)', (id, d))

    def _update_category(self, cr, uid, id, category='Uncategorized'):
        categs = category.split('/')
        p_id = None
        while categs:
            if p_id is not None:
                cr.execute('select id from ir_module_category where name=%s and parent_id=%d', (categs[0], p_id))
            else:
                cr.execute('select id from ir_module_category where name=%s and parent_id is NULL', (categs[0],))
            c_id = cr.fetchone()
            if not c_id:
                cr.execute('select nextval(\'ir_module_category_id_seq\')')
                c_id = cr.fetchone()[0]
                cr.execute('insert into ir_module_category (id, name, parent_id) values (%d, %s, %d)', (c_id, categs[0], p_id))
            else:
                c_id = c_id[0]
            p_id = c_id
            categs = categs[1:]
        self.write(cr, uid, [id], {'category_id': p_id})

    def action_install(self,cr,uid,ids,context=None):
        self.write(cr , uid, ids ,{'state' : 'to install'})        
        self.download(cr, uid, ids, context=context)
        for id in ids:
            cr.execute("select m.id as id from ir_module_module_dependency d inner join ir_module_module m on (m.name=d.name) where d.module_id=%d and m.state='uninstalled'",(id,))
            dep_ids = map(lambda x:x[0],cr.fetchall())
            if len(dep_ids):                    
                self.action_install(cr,uid,dep_ids,context=context)

    def update_translations(self, cr, uid, ids, filter_lang=None):
        logger = netsvc.Logger()

        if not filter_lang:
            pool = pooler.get_pool(cr.dbname)
            lang_obj=pool.get('res.lang')
            lang_ids=lang_obj.search(cr, uid, [('translatable', '=', True)])
            filter_lang= [lang.code for lang in lang_obj.browse(cr, uid, lang_ids)]
        elif not isinstance(filter_lang, (list, tuple)):
            filter_lang = [filter_lang]

        for mod in self.browse(cr, uid, ids):
            if mod.state != 'installed':
                continue
            
            for lang in filter_lang:
                f = os.path.join(tools.config['addons_path'], mod.name, 'i18n', lang + '.po')
                if os.path.exists(f):
                    logger.notifyChannel("init", netsvc.LOG_INFO, 'addons %s: loading translation file for language %s' % (mod.name, lang))
                    tools.trans_load(cr.dbname, f, lang, verbose=False)

module()

class module_dependency(osv.osv):
    _name = "ir.module.module.dependency"
    _description = "Module dependency"

    def _state(self, cr, uid, ids, name, args, context={}):
        result = {}
        mod_obj = self.pool.get('ir.module.module')
        for md in self.browse(cr, uid, ids):
            ids = mod_obj.search(cr, uid, [('name', '=', md.name)])
            if ids:
                result[md.id] = mod_obj.read(cr, uid, [ids[0]], ['state'])[0]['state']
            else:
                result[md.id] = 'unknown'
        return result

    _columns = {
        'name': fields.char('Name',  size=128),
        'module_id': fields.many2one('ir.module.module', 'Module', select=True, ondelete='cascade'),
        'state': fields.function(_state, method=True, type='selection', selection=[
            ('uninstallable','Uninstallable'),
            ('uninstalled','Not Installed'),
            ('installed','Installed'),
            ('to upgrade','To be upgraded'),
            ('to remove','To be removed'),
            ('to install','To be installed'),
            ('unknown', 'Unknown'),
            ], string='State', readonly=True),
    }
module_dependency()



class module_config_wizard_step(osv.osv):
    _name = 'ir.module.module.configuration.step'
    _columns={
        'name':fields.char('Name',size=64,required=True, select=True),
        'note':fields.text('Text'),
        'action_id':fields.many2one('ir.actions.act_window', 'Action', select=True,required=True, ondelete='cascade'),
        'sequence':fields.integer('Sequence'),
        'state':fields.selection([('open', 'Not Started'),('done', 'Done'),('skip','Skipped')], string='State', required=True)
    }
    _defaults={
        'state': lambda *a: 'open',
        'sequence': lambda *a: 10,
    }
    _order="sequence"
module_config_wizard_step()


class module_configuration(osv.osv_memory):
    _name='ir.module.module.configuration.wizard'
    def _get_action_name(self, cr, uid, context={}):
        item_obj = self.pool.get('ir.module.module.configuration.step')
        item_ids = item_obj.search(cr, uid, [
            ('state', '=', 'open'),
            ], limit=1, context=context)
        if item_ids and len(item_ids):
            item = item_obj.browse(cr, uid, item_ids[0], context=context)
            return item.note
        else:
            return "Your database is now fully configured.\n\nClick 'Continue' and enjoy your OpenERP experience..."
        return False

    def _get_action(self, cr, uid, context={}):
        item_obj = self.pool.get('ir.module.module.configuration.step')
        item_ids = item_obj.search(cr, uid, [
            ('state', '=', 'open'),
            ], limit=1, context=context)
        if item_ids:
            item = item_obj.browse(cr, uid, item_ids[0], context=context)
            return item.id
        return False

    def _progress_get(self,cr,uid, context={}):
        total = self.pool.get('ir.module.module.configuration.step').search_count(cr, uid, [], context)
        todo = self.pool.get('ir.module.module.configuration.step').search_count(cr, uid, [('state','<>','open')], context)
        return max(5.0,round(todo*100/total))

    _columns = {
        'name': fields.text('Next Wizard',readonly=True),
        'progress': fields.float('Configuration Progress', readonly=True),
        'item_id':fields.many2one('ir.module.module.configuration.step', 'Next Configuration Wizard',invisible=True, readonly=True),
    }
    _defaults={
        'progress': _progress_get,
        'item_id':_get_action,
        'name':_get_action_name,
    }
    def button_skip(self,cr,uid,ids,context=None):
        item_obj = self.pool.get('ir.module.module.configuration.step')
        item_id=self.read(cr,uid,ids)[0]['item_id']
        if item_id:
            item = item_obj.browse(cr, uid, item_id, context=context)
            item_obj.write(cr, uid, item.id, {
                'state': 'skip',
                }, context=context)
            return{
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.module.module.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }
        return {'type':'ir.actions.act_window_close'}

    def button_continue(self, cr, uid, ids, context=None):
        item_obj = self.pool.get('ir.module.module.configuration.step')
        item_id=self.read(cr,uid,ids)[0]['item_id']
        if item_id:
            item = item_obj.browse(cr, uid, item_id, context=context)
            item_obj.write(cr, uid, item.id, {
                'state': 'done',
                }, context=context)
            return{
                  'view_type': item.action_id.view_type,
                  'view_id':item.action_id.view_id and [item.action_id.view_id.id] or False,
                  'res_model': item.action_id.res_model,
                  'type': item.action_id.type,
                  'target':item.action_id.target,
            }
        return {'type':'ir.actions.act_window_close' }
module_configuration()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

