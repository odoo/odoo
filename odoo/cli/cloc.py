# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import config
from odoo.tools import cloc


def main():
    if not config['clocpaths'] and not config['db_name']:
        raise SystemExit('Missing --path or --database')

    c = cloc.Cloc()
    if config['db_name']:
        c.count_database(config['db_name'])
    for path in config['clocpaths']:
        c.count_path(path)
    c.report(config['verbose'])
