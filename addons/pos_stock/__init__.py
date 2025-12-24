from . import receipt
from . import models


def uninstall_hook(env):
    # The search domain is based on how the sequence is defined in the _get_sequence_values method in /addons/pos_stock/models/stock_warehouse.py
    env['ir.sequence'].search([('name', 'ilike', '%Picking POS%'), ('prefix', 'ilike', '%/POS/%')]).unlink()
