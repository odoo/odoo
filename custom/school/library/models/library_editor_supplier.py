# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class LibraryEditorSupplier(models.Model):
    _name = "library.editor.supplier"
    _description = "Editor Relations"

    name = fields.Many2one('res.partner', 'Editor')
    supplier_id = fields.Many2one('res.partner', 'Supplier')
    sequence = fields.Integer('Sequence')
    delay = fields.Integer('Customer Lead Time')
    min_qty = fields.Float('Minimal Quantity')
    junk = fields.Text(compute_=lambda self: dict([(idn, '')
                       for idn in self.ids]),
                       method=True, string=" ", type="text")

#     @api.model
#     @api.returns('self', lambda value: value)
#     def create(self, vals):
#         if not (vals['name'] and vals['supplier_id']):
#             raise UserError(_("Error ! Please provide proper Information"))
#         # search for books of these editor not already linked
#         # with this supplier:
#         select = """select product_tmpl_id\n"""\
#                  """from product_product\n"""\
#                  """where editor = %s\n"""\
#                  """  and id not in (select product_tmpl_id\
#                  from product_supplierinfo where name = %s)"""\
#                  % (vals['name'], vals['supplier_id'])
#         self._cr.execute(select)
#         if not self._cr.rowcount:
#             raise UserError(_("Error ! No book to apply this relation"))
#         sup_info = self.env['product.supplierinfo']
#         last_id = 0
#         for book_id in self._cr.fetchall():
#             params = {'name': vals['supplier_id'],
#                       'product_tmpl_id': book_id[0],
#                       'sequence': vals['sequence'],
#                       'delay': vals['delay'],
#                       'min_qty': vals['min_qty']}
#             tmp_id = sup_info.create(params)
#             last_id = last_id < tmp_id.id and last_id or tmp_id.id
#         return last_id
#     @api.multi
#     def write(self, vals):
#         res = {}
#         update_sequence = "update product_supplierinfo\
#                            set sequence = %s where name = %s"
#         update_delay = "update product_supplierinfo\
#                         set delay = %s where name = %s"
#         for rel, idn in zip(self, self.ids):
#             original_supplier_id = rel.supplier_id.id
#             if not original_supplier_id:
#                 raise UserError(_('Warning ! Cannot set supplier in this\
#                                     form Please create a new relation.'))
#             new_supplier_id = vals.get('supplier_id', 0)
#             check_supp = (idn < 0 or (original_supplier_id !=\
#                                         new_supplier_id))
#             supplier_change = new_supplier_id != 0 and check_supp
#             if supplier_change:
#                 raise UserError(_('Warning!Cannot set supplier in this form.'
#                                   'Please create a new relation.'))
#             else:
#                 if 'sequence' in vals:
#                     params = [vals.get('sequence', 0), original_supplier_id]
#                     self._cr.execute(update_sequence, params)
#                 if 'delay' in vals:
#                     params = [vals.get('delay', 0), original_supplier_id]
#                     self._cr.execute(update_delay, params)
#                 res[str(idn)] = {}
#         return res
