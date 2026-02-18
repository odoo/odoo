# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
# from . import wizard
from . import controllers
from odoo.tools import convert


def import_csv_data(env):
    filenames = ['data/res.city.csv', 'data/district.csv', 'data/area.csv']
    for filename in filenames:
        convert.convert_file(
            env, 'delivery_shipper',
            filename, None, mode='init', noupdate=True,
            kind='init'
        )


def post_init(env):
    import_csv_data(env)
