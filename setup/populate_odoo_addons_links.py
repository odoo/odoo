#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Populate odoo/addons directury with symlinks to all modules in addons/
This will make those addons available by default in the odoo.addons namespace,
and enables pip installation directly from GitHub source archives:

pip install https://github.com/owner/repo/archive/branch.zip
"""

import os

def main():
    script_path = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.join(script_path, '..')
    odoo_addons_path = os.path.join(root_path, 'odoo', 'addons')
    os.chdir(odoo_addons_path)
    addons_path = os.path.join('..', '..', 'addons')
    for dirname in sorted(os.listdir(addons_path)):
        orig_path = os.path.join(addons_path, dirname)
        try:
            os.symlink(orig_path, dirname)
            print "Created %s" % orig_path
        except OSError:
            os.unlink(dirname)
            os.symlink(orig_path, dirname)
            print "Replaced %s" % orig_path

if __name__ == '__main__':
    main()
