from odoo import SUPERUSER_ID, api
from .tools import create_journals


def generate_tax_adjustments_journal(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    create_journals(env)
