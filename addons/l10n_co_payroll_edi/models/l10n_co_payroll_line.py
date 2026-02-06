# Part of GPCB. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

# Colombian payroll concept codes per DIAN Technical Annex
EARNING_CONCEPTS = [
    ('salary', 'Salario', 'SAL'),
    ('transport', 'Auxilio de Transporte', 'ATR'),
    ('overtime_hed', 'Hora Extra Diurna (25%)', 'HED'),
    ('overtime_hen', 'Hora Extra Nocturna (75%)', 'HEN'),
    ('overtime_heddf', 'Hora Extra Diurna Dom/Fest (100%)', 'HEDDF'),
    ('overtime_hendf', 'Hora Extra Nocturna Dom/Fest (150%)', 'HENDF'),
    ('overtime_hrn', 'Recargo Nocturno (35%)', 'HRN'),
    ('overtime_hrndf', 'Recargo Nocturno Dom/Fest (110%)', 'HRNDF'),
    ('commission', 'Comisiones', 'COM'),
    ('bonus', 'Bonificación', 'BON'),
    ('vacation', 'Vacaciones', 'VAC'),
    ('prima', 'Prima de Servicios', 'PRI'),
    ('cesantias', 'Cesantías', 'CES'),
    ('cesantias_interest', 'Intereses de Cesantías', 'ICE'),
    ('disability', 'Incapacidad', 'INC'),
    ('maternity', 'Licencia Maternidad/Paternidad', 'LMP'),
    ('other_earning', 'Otros Devengados', 'OTD'),
]

DEDUCTION_CONCEPTS = [
    ('health_eps', 'Salud (EPS) 4%', 'EPS'),
    ('pension_afp', 'Pensión (AFP) 4%', 'AFP'),
    ('solidarity_fsp', 'Fondo de Solidaridad Pensional', 'FSP'),
    ('rtefte', 'Retención en la Fuente', 'RFT'),
    ('union_dues', 'Cuotas Sindicales', 'SIN'),
    ('voluntary', 'Deducción Voluntaria', 'VOL'),
    ('embargo', 'Embargo Judicial', 'EMB'),
    ('other_deduction', 'Otras Deducciones', 'OTR'),
]

PROVISION_CONCEPTS = [
    ('health_employer', 'Salud Empleador (EPS 8.5%)', 'EPE'),
    ('pension_employer', 'Pensión Empleador (AFP 12%)', 'APE'),
    ('arl', 'ARL (Riesgos Laborales)', 'ARL'),
    ('sena', 'SENA (2%)', 'SEN'),
    ('icbf', 'ICBF (3%)', 'ICB'),
    ('caja', 'Caja de Compensación (4%)', 'CCF'),
    ('cesantias_prov', 'Provisión Cesantías (8.33%)', 'PCE'),
    ('cesantias_int_prov', 'Provisión Intereses Cesantías (1%)', 'PIC'),
    ('prima_prov', 'Provisión Prima (8.33%)', 'PPR'),
    ('vacation_prov', 'Provisión Vacaciones (4.17%)', 'PVA'),
]


def _get_concept_selection(concepts):
    return [(c[0], c[1]) for c in concepts]


ALL_CONCEPTS = EARNING_CONCEPTS + DEDUCTION_CONCEPTS + PROVISION_CONCEPTS
CONCEPT_CODE_MAP = {c[0]: c[2] for c in ALL_CONCEPTS}


class L10nCoPayrollDocumentLine(models.Model):
    _name = 'l10n_co.payroll.document.line'
    _description = 'Payroll Document Line'
    _order = 'line_type, sequence'

    document_id = fields.Many2one(
        'l10n_co.payroll.document', required=True, ondelete='cascade',
    )
    line_type = fields.Selection(
        selection=[
            ('earning', 'Earning'),
            ('deduction', 'Deduction'),
            ('provision', 'Provision'),
        ],
        string='Type', required=True,
    )
    sequence = fields.Integer(default=10)
    concept = fields.Char(string='Concept', required=True)
    concept_code = fields.Char(
        string='DIAN Code', compute='_compute_concept_code', store=True,
    )
    amount = fields.Monetary(
        string='Amount', required=True, currency_field='currency_id',
    )
    rate = fields.Float(string='Rate (%)')
    quantity = fields.Float(string='Quantity')
    account_id = fields.Many2one(
        'account.account', string='Account',
        help='Accounting account for journal entry generation.',
    )
    currency_id = fields.Many2one(
        'res.currency', related='document_id.currency_id',
    )

    @api.depends('concept')
    def _compute_concept_code(self):
        for line in self:
            # Try to match concept name to a known code
            concept_lower = (line.concept or '').lower()
            code = ''
            for key, dian_code in CONCEPT_CODE_MAP.items():
                if key in concept_lower or concept_lower in key:
                    code = dian_code
                    break
            line.concept_code = code
