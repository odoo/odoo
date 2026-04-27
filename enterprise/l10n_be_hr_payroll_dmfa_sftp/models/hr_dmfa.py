# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrDMFAReport(models.Model):
    _name = "l10n_be.dmfa"
    _inherit = ["l10n_be.dmfa", "mail.thread", "mail.activity.mixin"]

    onss_declaration_ids = fields.One2many('l10n.be.onss.declaration', 'dmfa_id')
    onss_declaration_count = fields.Integer(compute='_compute_onss_declaration_count')

    @api.depends('onss_declaration_ids')
    def _compute_onss_declaration_count(self):
        for dmfa in self:
            dmfa.onss_declaration_count = len(dmfa.onss_declaration_ids)

    def action_open_onss_declaration(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('l10n_be_hr_payroll_dmfa_sftp.action_l10n_be_onss_declaration')
        action.update({
            'domain': [('dmfa_id', '=', self.id)],
            'context': {'default_dmfa_id': self.id}
        })
        return action

    def action_create_onss_declaration(self):
        self.ensure_one()
        if self.declaration_type != "batch":
            raise UserError(_("DmfA Declaration type should be via batch"))
        onss_declaration = self.env['l10n.be.onss.declaration'].create({
            'dmfa_id': self.id,
            'environment': self.file_type,
        })
        onss_file_vals = [{
            'name': self[f"{field}_filename"],
            'file': self[field],
            'onss_declaration_id': onss_declaration.id,
        } for field in ["dmfa_xml", "dmfa_signature", "dmfa_go"] if self[field]]
        self.env['l10n.be.onss.file'].create(onss_file_vals)
        self.message_post(body=_(
            'The draft %(declaration)s (id=%(declaration_id)s) has been created',
            declaration=onss_declaration._get_html_link(_('declaration')),
            declaration_id=onss_declaration.id))

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': onss_declaration.id,
            'res_model': 'l10n.be.onss.declaration',
            'target': 'current',
        }
