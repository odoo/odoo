from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )

    l10n_es_tax_plan = fields.Selection(
        selection=[
            ('aeat', 'AEAT'),
            ('hacienda_foral_bizkaia', 'Hacienda Foral Bizkaia'),
            ('hacienda_foral_gipuzkoa', 'Hacienda Foral Guipuzkoa'),
            ('hacienda_foral_alava', 'Hacienda Foral Álava'),
            ('igic', 'IGIC (Canarias)'),
            ('ipsi', 'IPSI (Ceuta y Melilla)'),
        ],
        string='Hacienda',
        help='Select tax plan',
        default='aeat'
    )

    l10n_es_edi = fields.Selection(
        selection=[
            ('verifactu', 'Veri*Factu'),
            ('sii', 'SII'),
            ('tbai', 'TicketBAI')
        ],
        string='EDIs'
    )

    l10n_es_irpf_regime = fields.Selection(
        selection=[
            ('direct', 'Estimación directa'),
            ('direct_simplified', 'Estimación directa simplificada'),
            ('objective', 'Estimación objetiva')
        ],
        string='Régimenes IRPF'
    )

    module_l10n_es_real_estates = fields.Boolean('Real Estate')
    intracomunitary_oss = fields.Boolean('Intracomunitary, OSS')
    igic = fields.Boolean('IGIC')
    aeat = fields.Boolean('AEAT')

    def _l10n_es_get_pos_edi_mode(self):
        """Return the POS EDI mode for this company.
        Returns 'tbai', 'verifactu', or False (standard session closing entry).
        """
        self.ensure_one()
        return False

    def write(self, vals):
        tax_plan_changed = 'l10n_es_tax_plan' in vals
        aeat_changed = 'aeat' in vals
        igic_changed = 'igic' in vals
        aeat_value = vals.get('aeat')
        igic_value = vals.get('igic')

        if tax_plan_changed:
            vals.setdefault('aeat', False)
            vals.setdefault('igic', False)

        if vals.get('aeat'):
            vals['igic'] = False
        if vals.get('igic'):
            vals['aeat'] = False

        res = super().write(vals)

        for company in self:
            template = self.env['account.chart.template'].with_company(company)
            if tax_plan_changed:
                template._l10n_es_manage_dynamic_taxes(company, company.l10n_es_tax_plan, archive_other=True)
                template._l10n_es_manage_dynamic_reports(company, company.l10n_es_tax_plan, archive_other=True)
            elif aeat_changed:
                template._l10n_es_manage_dynamic_taxes(company, 'aeat', archive_other=False, activate=aeat_value)
                template._l10n_es_manage_dynamic_reports(company, 'aeat', archive_other=False, activate=aeat_value)
            elif igic_changed:
                template._l10n_es_manage_dynamic_taxes(company, 'igic', archive_other=False, activate=igic_value)
                template._l10n_es_manage_dynamic_reports(company, 'igic', archive_other=False, activate=igic_value)
        return res
