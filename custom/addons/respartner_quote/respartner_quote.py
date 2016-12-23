from openerp import models, fields, api, tools, _
import logging

_logger = logging.getLogger(__name__)

class res_partner(models.Model):
    _inherit = 'res.partner'
    mom_company_id = fields.Many2one('res.partner', string="Mother Company")

    @api.onchange('parent_id')
    def _onchange_partner_id(self):
        parent = self.env['res.partner'].browse(self.parent_id.id)
        if parent:
            self.phone = parent.phone
            self.fax = parent.fax
            self.lang = parent.lang
        return super(res_partner, self).onchange_parent_id(self)
