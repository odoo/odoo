# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nCoWithholdingCertificateWizard(models.TransientModel):
    _name = 'l10n_co.withholding.certificate.wizard'
    _description = 'Generate Withholding Certificates'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    date_from = fields.Date(string='Period Start', required=True)
    date_to = fields.Date(string='Period End', required=True)
    certificate_type = fields.Selection(
        selection=[
            ('rtefte', 'RteFte (Income Withholding)'),
            ('rteiva', 'RteIVA (VAT Withholding)'),
            ('rteica', 'RteICA (Municipal Withholding)'),
            ('all', 'All Withholdings'),
        ],
        string='Type',
        default='all',
        required=True,
    )
    partner_ids = fields.Many2many(
        'res.partner', string='Specific Partners',
        help='Leave empty to generate for all partners with withholdings in the period.',
    )

    def action_generate(self):
        """Generate withholding certificates for the selected period."""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(_('Period start date must be before end date.'))

        # Find partners with withholding entries in the period
        domain = [
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('tax_line_id', '!=', False),
        ]
        move_lines = self.env['account.move.line'].search(domain)

        # Get the group prefixes for filtering
        cert_model = self.env['l10n_co.withholding.certificate']
        temp_cert = cert_model.new({'certificate_type': self.certificate_type})
        group_prefixes = temp_cert._get_group_prefixes()

        # Filter to withholding taxes only
        wh_lines = move_lines.filtered(
            lambda ml: any(
                (ml.tax_line_id.tax_group_id.name or '').upper().startswith(p)
                for p in group_prefixes
            )
        )

        partner_ids = wh_lines.mapped('partner_id')
        if self.partner_ids:
            partner_ids &= self.partner_ids

        if not partner_ids:
            raise UserError(_(
                'No withholding entries found for the selected period and type.'
            ))

        certificates = self.env['l10n_co.withholding.certificate']
        for partner in partner_ids:
            cert = cert_model.create({
                'company_id': self.company_id.id,
                'partner_id': partner.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'certificate_type': self.certificate_type,
            })
            cert.action_compute_lines()
            # Only keep certificates that have actual lines
            if cert.line_ids:
                certificates |= cert
            else:
                cert.unlink()

        if not certificates:
            raise UserError(_(
                'No withholding data found for the selected partners and period.'
            ))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Certificates'),
            'res_model': 'l10n_co.withholding.certificate',
            'domain': [('id', 'in', certificates.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }
