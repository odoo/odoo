# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import controllers


def post_init_hook(env):
    env['hr.work.entry.type']._archive_generic_types()
