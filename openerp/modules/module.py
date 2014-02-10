# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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

import base64
import imp
import itertools
import logging
import os
import re
import sys
import types
from cStringIO import StringIO
from os.path import join as opj

import unittest2

import openerp
import openerp.tools as tools
import openerp.release as release
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('openerp.tests')

# addons path ','.joined
_ad = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'addons') # default addons path (base)

# addons path as a list
ad_paths = []

# Modules already loaded
loaded = []

_logger = logging.getLogger(__name__)

class AddonsImportHook(object):
    """
    Import hook to load OpenERP addons from multiple paths.

    OpenERP implements its own import-hook to load its addons. OpenERP
    addons are Python modules. Originally, they were each living in their
    own top-level namespace, e.g. the sale module, or the hr module. For
    backward compatibility, `import <module>` is still supported. Now they
    are living in `openerp.addons`. The good way to import such modules is
    thus `import openerp.addons.module`.
    """

    def find_module(self, module_name, package_path):
        module_parts = module_name.split('.')
        if len(module_parts) == 3 and module_name.startswith('openerp.addons.'):
            return self # We act as a loader too.

    def load_module(self, module_name):

        module_parts = module_name.split('.')
        if len(module_parts) == 3 and module_name.startswith('openerp.addons.'):
            module_part = module_parts[2]
            if module_name in sys.modules:
                return sys.modules[module_name]

        # Note: we don't support circular import.
        f, path, descr = imp.find_module(module_part, ad_paths)
        mod = imp.load_module('openerp.addons.' + module_part, f, path, descr)
        sys.modules['openerp.addons.' + module_part] = mod
        return mod

def initialize_sys_path():
    """
    Setup an import-hook to be able to import OpenERP addons from the different
    addons paths.

    This ensures something like ``import crm`` (or even
    ``import openerp.addons.crm``) works even if the addons are not in the
    PYTHONPATH.
    """
    global ad_paths
    if ad_paths:
        return

    ad_paths = map(lambda m: os.path.abspath(tools.ustr(m.strip())), tools.config['addons_path'].split(','))
    ad_paths.append(os.path.abspath(_ad)) # for get_module_path
    sys.meta_path.append(AddonsImportHook())

def get_module_path(module, downloaded=False, display_warning=True):
    """Return the path of the given module.

    Search the addons paths and return the first path where the given
    module is found. If downloaded is True, return the default addons
    path if nothing else is found.

    """
    initialize_sys_path()
    for adp in ad_paths:
        if os.path.exists(opj(adp, module)) or os.path.exists(opj(adp, '%s.zip' % module)):
            return opj(adp, module)

    if downloaded:
        return opj(_ad, module)
    if display_warning:
        _logger.warning('module %s: module not found', module)
    return False

def get_module_filetree(module, dir='.'):
    path = get_module_path(module)
    if not path:
        return False

    dir = os.path.normpath(dir)
    if dir == '.':
        dir = ''
    if dir.startswith('..') or (dir and dir[0] == '/'):
        raise Exception('Cannot access file outside the module')

    files = openerp.tools.osutil.listdir(path, True)

    tree = {}
    for f in files:
        if not f.startswith(dir):
            continue

        if dir:
            f = f[len(dir)+int(not dir.endswith('/')):]
        lst = f.split(os.sep)
        current = tree
        while len(lst) != 1:
            current = current.setdefault(lst.pop(0), {})
        current[lst.pop(0)] = None

    return tree

def get_module_resource(module, *args):
    """Return the full path of a resource of the given module.

    :param module: module name
    :param list(str) args: resource path components within module

    :rtype: str
    :return: absolute path to the resource

    TODO name it get_resource_path
    TODO make it available inside on osv object (self.get_resource_path)
    """
    mod_path = get_module_path(module)
    if not mod_path: return False
    resource_path = opj(mod_path, *args)
    if os.path.isdir(mod_path):
        # the module is a directory - ignore zip behavior
        if os.path.exists(resource_path):
            return resource_path
    return False

def get_module_icon(module):
    iconpath = ['static', 'description', 'icon.png']
    if get_module_resource(module, *iconpath):
        return ('/' + module + '/') + '/'.join(iconpath)
    return '/base/'  + '/'.join(iconpath)

def load_information_from_description_file(module):
    """
    :param module: The name of the module (sale, purchase, ...)
    """

    terp_file = get_module_resource(module, '__openerp__.py')
    mod_path = get_module_path(module)
    if terp_file:
        info = {}
        if os.path.isfile(terp_file):
            # default values for descriptor
            info = {
                'application': False,
                'author': '',
                'auto_install': False,
                'category': 'Uncategorized',
                'depends': [],
                'description': '',
                'icon': get_module_icon(module),
                'installable': True,
                'license': 'AGPL-3',
                'name': False,
                'post_load': None,
                'version': '1.0',
                'web': False,
                'website': '',
                'sequence': 100,
                'summary': '',
            }
            info.update(itertools.izip(
                'depends data demo test init_xml update_xml demo_xml'.split(),
                iter(list, None)))

            f = tools.file_open(terp_file)
            try:
                info.update(eval(f.read()))
            finally:
                f.close()

            if 'active' in info:
                # 'active' has been renamed 'auto_install'
                info['auto_install'] = info['active']

            info['version'] = adapt_version(info['version'])
            return info

    #TODO: refactor the logger in this file to follow the logging guidelines
    #      for 6.0
    _logger.debug('module %s: no __openerp__.py file found.', module)
    return {}

def init_module_models(cr, module_name, obj_list):
    """ Initialize a list of models.

    Call _auto_init and init on each model to create or update the
    database tables supporting the models.

    TODO better explanation of _auto_init and init.

    """
    _logger.info('module %s: creating or updating database tables', module_name)
    todo = []
    for obj in obj_list:
        result = obj._auto_init(cr, {'module': module_name})
        if result:
            todo += result
        if hasattr(obj, 'init'):
            obj.init(cr)
        cr.commit()
    for obj in obj_list:
        obj._auto_end(cr, {'module': module_name})
        cr.commit()
    todo.sort()
    for t in todo:
        t[1](cr, *t[2])
    cr.commit()

def load_openerp_module(module_name):
    """ Load an OpenERP module, if not already loaded.

    This loads the module and register all of its models, thanks to either
    the MetaModel metaclass, or the explicit instantiation of the model.
    This is also used to load server-wide module (i.e. it is also used
    when there is no model to register).
    """
    global loaded
    if module_name in loaded:
        return

    initialize_sys_path()
    try:
        mod_path = get_module_path(module_name)
        __import__('openerp.addons.' + module_name)

        # Call the module's post-load hook. This can done before any model or
        # data has been initialized. This is ok as the post-load hook is for
        # server-wide (instead of registry-specific) functionalities.
        info = load_information_from_description_file(module_name)
        if info['post_load']:
            getattr(sys.modules['openerp.addons.' + module_name], info['post_load'])()

    except Exception, e:
        msg = "Couldn't load module %s" % (module_name)
        _logger.critical(msg)
        _logger.critical(e)
        raise
    else:
        loaded.append(module_name)

def get_modules():
    """Returns the list of module names
    """
    def listdir(dir):
        def clean(name):
            name = os.path.basename(name)
            if name[-4:] == '.zip':
                name = name[:-4]
            return name

        def is_really_module(name):
            manifest_name = opj(dir, name, '__openerp__.py')
            zipfile_name = opj(dir, name)
            return os.path.isfile(manifest_name)
        return map(clean, filter(is_really_module, os.listdir(dir)))

    plist = []
    initialize_sys_path()
    for ad in ad_paths:
        plist.extend(listdir(ad))
    return list(set(plist))

def get_modules_with_version():
    modules = get_modules()
    res = dict.fromkeys(modules, adapt_version('1.0'))
    for module in modules:
        try:
            info = load_information_from_description_file(module)
            res[module] = info['version']
        except Exception:
            continue
    return res

def adapt_version(version):
    serie = release.major_version
    if version == serie or not version.startswith(serie + '.'):
        version = '%s.%s' % (serie, version)
    return version

def get_test_modules(module):
    """ Return a list of module for the addons potentialy containing tests to
    feed unittest2.TestLoader.loadTestsFromModule() """
    # Try to import the module
    module = 'openerp.addons.' + module + '.tests'
    try:
        m = __import__(module)
    except Exception, e:
        # If module has no `tests` sub-module, no problem.
        if str(e) != 'No module named tests':
            _logger.exception('Can not `import %s`.', module)
        return []

    # include submodules too
    result = []
    for name in sys.modules:
        if name.startswith(module) and sys.modules[name]:
            result.append(sys.modules[name])
    return result

# Use a custom stream object to log the test executions.
class TestStream(object):
    def __init__(self):
        self.r = re.compile(r'^-*$|^ *... *$|^ok$')
    def flush(self):
        pass
    def write(self, s):
        if self.r.match(s):
            return
        first = True
        for c in s.split('\n'):
            if not first:
                c = '` ' + c
            first = False
            _test_logger.info(c)

def run_unit_tests(module_name, dbname):
    """
    Return True or False if some tests were found and succeeded or failed.
    Return None if no test was found.
    """
    mods = get_test_modules(module_name)
    r = True
    for m in mods:
        suite = unittest2.TestSuite()
        for t in unittest2.TestLoader().loadTestsFromModule(m):
            suite.addTest(t)
        _logger.log(logging.INFO, 'module %s: running test %s.', module_name, m.__name__)
        result = unittest2.TextTestRunner(verbosity=2, stream=TestStream()).run(suite)
        if not result.wasSuccessful():
            r = False
            _logger.error('module %s: at least one error occurred in a test', module_name)
    return r

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
