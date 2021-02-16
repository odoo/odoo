# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, fields, models


class IrAttachment(models.AbstractModel):
    _inherit = 'ir.attachment'

    # Here for all kinds of integration e.g. file component, reporting
    formio_form_id = fields.Many2one(
        'formio.form', compute='_compute_formio_form_id', store=True, default=False, index=True)

    @api.depends('res_model')
    def _compute_formio_form_id(self):
        for attach in self:
            if attach.res_model == 'formio.form' and attach.res_id:
                # XXX optimize with 1 browse(ids) query and write on records?
                form = self.env['formio.form'].browse(attach.res_id)
                attach.formio_form_id = form.id

    @api.model
    def check(self, mode, values=None):
        to_check = self
        if self.ids:
            self._cr.execute("SELECT id FROM ir_attachment WHERE res_model = 'formio.version.asset' AND id IN %s", [tuple(self.ids)])
            asset_ids = [r[0] for r in self._cr.fetchall()]
            if asset_ids:
                to_check = self - self.browse(asset_ids)
        super(IrAttachment, to_check).check(mode, values)
