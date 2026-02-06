# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nCoEdiExogenousWizard(models.TransientModel):
    _name = 'l10n_co_edi.exogenous.wizard'
    _description = 'Generate Exogenous Information Documents'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    year = fields.Integer(
        string='Tax Year', required=True,
        default=lambda self: fields.Date.context_today(self).year - 1,
    )
    formato_ids = fields.Selection(
        selection=[
            ('all', 'All Formatos'),
            ('1001', 'Formato 1001 - Pagos y Retenciones'),
            ('1003', 'Formato 1003 - Retenciones Practicadas'),
            ('1005', 'Formato 1005 - IVA Deducible'),
            ('1006', 'Formato 1006 - IVA Generado'),
            ('1007', 'Formato 1007 - Ingresos Recibidos'),
        ],
        string='Formato', default='all', required=True,
    )

    def action_generate(self):
        """Generate exogenous information documents for the selected year/formato."""
        self.ensure_one()

        if self.year < 2000 or self.year > 2100:
            raise UserError(_('Please enter a valid tax year.'))

        ExoDoc = self.env['l10n_co_edi.exogenous.document']

        if self.formato_ids == 'all':
            formatos = ['1001', '1003', '1005', '1006', '1007']
        else:
            formatos = [self.formato_ids]

        documents = self.env['l10n_co_edi.exogenous.document']
        for fmt in formatos:
            # Check if document already exists
            existing = ExoDoc.search([
                ('company_id', '=', self.company_id.id),
                ('year', '=', self.year),
                ('formato', '=', fmt),
            ], limit=1)

            if existing and existing.state != 'draft':
                continue  # Skip non-draft duplicates

            if existing:
                doc = existing
            else:
                doc = ExoDoc.create({
                    'company_id': self.company_id.id,
                    'year': self.year,
                    'formato': fmt,
                })

            doc.action_compute_lines()
            documents |= doc

        if not documents:
            raise UserError(_(
                'No new documents to generate. Existing documents for year %s '
                'are already confirmed or sent.', self.year,
            ))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Exogenous Documents — %s', self.year),
            'res_model': 'l10n_co_edi.exogenous.document',
            'domain': [('id', 'in', documents.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }
