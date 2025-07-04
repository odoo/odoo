from odoo import _, fields, models


class L10nTrNilveraEreceiptImport(models.TransientModel):
    _name = 'l10n_tr.nilvera.ereceipt.import'
    _description = 'Wizard to import E-receipt XML obtained from Nilvera Portal'

    def _default_warehouse_id(self):
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        return warehouse_id.id

    warehouse_id = fields.Many2one(string="Warehouse", comodel_name='stock.warehouse', default=_default_warehouse_id)
    ereceipt_file = fields.Json(string="Upload E-Receipt")

    def _import_receipt_from_xml(self, file_data):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse_id.in_type_id.id,
            'location_dest_id': self.warehouse_id.lot_stock_id.id,
        })
        picking._update_data_from_xml(file_data)
        return picking

    def _import_ereceipt_from_attachments(self, attachments):
        file_data_list = attachments._unwrap_edi_attachments()
        picking_ids = self.env['stock.picking']
        for file_data in file_data_list:
            picking = self._import_receipt_from_xml(file_data)
            picking_ids |= picking
        return picking_ids

    def action_import_receipt(self):
        if not self.ereceipt_file:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': _('Please attach E-Receipts'),
                },
            }
        attachment_ids = [attachment_data.get('id') for attachment_data in self.ereceipt_file]
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        picking_ids = self._import_ereceipt_from_attachments(attachments)
        action_vals = {
            'type': 'ir.actions.act_window',
            'name': _("Imported E-Receipts"),
            'res_model': 'stock.picking',
            'domain': [('id', 'in', picking_ids.ids)],
        }
        if len(picking_ids) == 1:
            action_vals.update({
                'views': [[False, "form"]],
                'view_mode': 'form',
                'res_id': picking_ids[0].id,
            })
        else:
            action_vals.update({
                'views': [[False, "list"], [False, "form"]],
                'view_mode': 'list, form',
            })
        return action_vals
