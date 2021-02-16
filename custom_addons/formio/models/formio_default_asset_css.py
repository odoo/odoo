# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, fields, models, _

import logging
logger = logging.getLogger(__name__)

class DefaultAssetCss(models.Model):
    _name = 'formio.default.asset.css'
    _description = 'Formio Asset CSS'

    attachment_id = fields.Many2one(
        'ir.attachment', string="Attachment",
        required=True, ondelete='cascade', domain=[('res_model', '=', 'formio.asset.css')],
        context={'default_res_model': 'formio.asset.css'})
    attachment_type = fields.Selection(related='attachment_id.type', string='Attachment Type', readonly=True)
    url = fields.Char(string='URL', compute='_compute_url')
    active = fields.Boolean()
    nodelete = fields.Boolean(string='No delete (core)', compute='_compute_fields')

    @api.depends('attachment_id')
    def _compute_url(self):
        for r in self:
            if not r.attachment_id:
                r.url = False
            elif r.attachment_type == 'url':
                r.url = r.attachment_id.url
            elif r.attachment_type == 'binary':
                r.url = '/web/content/{attachment_id}'.format(attachment_id=r.attachment_id.id)

    def _compute_fields(self):
        for r in self:
            if r.id:
                r.nodelete = r.get_external_id()[r.id].startswith('formio')
            else:
                r.nodelete = True
