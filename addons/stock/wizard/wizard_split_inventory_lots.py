import wizard
import netsvc
import pooler

import time
from osv import osv
from tools.translate import _

inv_form = '''<?xml version="1.0"?>
<form string="Split Inventory Line">
 <field name="prefix"/>
 <newline/>
 <field name="quantity"/>
</form>
'''
inv_fields = {
        'prefix': {
            'string': 'Prefix',
            'type': 'char',
            'size': 64,
        },
        'quantity': {
            'string': 'Quantity per lot',
            'type': 'float',
            'default': 1,
        }
}

def _check_production_lot(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    inv_obj = pool.get('stock.inventory.line').browse(cr, uid, data['id'])
    if not inv_obj.prod_lot_id:
        raise wizard.except_wizard(_('Caution!'), _('Before splitting the inventory lines, make sure the production lot is assigned to this product.'))
    return data['form']

def _split_lines(self, cr, uid, data, context):
    inv_id = data['id']

    pool = pooler.get_pool(cr.dbname)
    inv_line_obj = pool.get('stock.inventory.line')
    prodlot_obj = pool.get('stock.production.lot')

    ir_sequence_obj = pool.get('ir.sequence')

    sequence = ir_sequence_obj.get(cr, uid, 'stock.lot.serial')
    if not sequence:
        raise wizard.except_wizard(_('Error!'), _('No production sequence defined'))
    if data['form']['prefix']:
        sequence = data['form']['prefix'] + '/' + (sequence or '')

    inv = inv_line_obj.browse(cr, uid, [inv_id])[0]
    quantity = data['form']['quantity']
    prodlot_obj.write(cr, uid, inv.prod_lot_id.id, {'name':sequence})

    if quantity <= 0 or inv.product_qty == 0:
        return {}

    quantity_rest = inv.product_qty % quantity

    update_val = {
        'product_qty': quantity,
    }

    new_line = []
    for idx in range(int(inv.product_qty // quantity)):
        if idx:
            current_line = inv_line_obj.copy(cr, uid, inv.id, {'prod_lot_id': inv.prod_lot_id.id})
            new_line.append(current_line)
        else:
            current_line = inv.id
        inv_line_obj.write(cr, uid, [current_line], update_val)

    if quantity_rest > 0:
        idx = int(inv.product_qty // quantity)
        update_val['product_qty'] = quantity_rest

        if idx:
            current_line = inv_line_obj.copy(cr, uid, inv.id, {'prod_lot_id': inv.prod_lot_id.id})
            new_line.append(current_line)
        else:
            current_line = inv.id
        inv_line_obj.write(cr, uid, [current_line], update_val)

    return {}

class wizard_split_inventory_lots(wizard.interface):
    states = {
        'init': {
            'actions': [_check_production_lot],
            'result': {'type': 'form', 'arch': inv_form, 'fields': inv_fields, 'state': [('end', 'Cancel', 'gtk-cancel'), ('split', 'Ok', 'gtk-ok')]},
            },
        'split': {
            'actions': [_split_lines],
            'result': {'type':'state', 'state':'end'}
        }
    }

wizard_split_inventory_lots('stock.inventory.line.split')
