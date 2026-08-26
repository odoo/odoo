from . import controllers


def _post_load():
    from odoo.tools import config
    if 'kpi' not in config['server_wide_modules']:
        config['server_wide_modules'] = config['server_wide_modules'] + ['kpi']
