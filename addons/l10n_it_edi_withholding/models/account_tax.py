# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

WITHHOLDING_TYPE_SELECTION = [
    ('RT01', '[RT01] Withholding for persons'),
    ('RT02', '[RT02] Withholding for personal businesses'),
    ('RT03', '[RT03] INPS Pension fund contribution'),
    ('RT04', '[RT04] ENASARCO pension fund contribution'),
    ('RT05', '[RT05] ENPAM pension fund contribution'),
    ('RT06', '[RT06] Other pension fund contribution'),
]

WITHHOLDING_REASON_SELECTION = [
    ('A', '[A] Autonomous work in the fields of art or profession'),
    ('B', '[B] Income from the use of intellectual properties or patents or processes, formulas and informations in the fields of science, commerce or science'),
    ('C', '[C] Income from work as part of association groups or other cooperation determined by contracts'),
    ('D', '[D] Income as partner or founder of a corporation'),
    ('E', '[E] Income from client-related bill protests made by town secretaries'),
    ('G', '[G] Compensation for the end of a professional sport career'),
    ('H', '[H] Compensation for the end of a societary career (excluded those earned before 31.12.2003) and already taxed'),
    ('I', '[I] Compensation for the end of a notary career'),
    ('K', '[K] Civil service checks, ref art. 16 D.lgs. n.40 6/03/2017'),
    ('L', '[L] Income from the use of intellectual properties or patents or processes, formulas and informations in the fields of science, commerce or science, but not made by the author/inventor'),
    ('L1', '[L1] Income from the use of intellectual properties or patents or processes, formulas and informations in the fields of science, commerce or science, from someone who actively bought the use rights'),
    ('M', '[M] Autonomous work which isn\'t part of usual professional/artistic duties, or incomes due for an obligation to act, not to act, or to allow'),
    ('M1', '[M1] Incomes due for an obligation to act, not to act, or to allow'),
    ('M2', '[M2] Autonomous work which isn\'t part of usual professional/artistic duties, or incomes due for an obligation to act, not to act, or to allow - that require being registered to the "Gestione separata"'),
    ('N', '[N] Compensation for travel, expenses, prizes, or other compensations for amateur sport activities'),
    ('O', '[O] Autonomous work which isn\'t part of usual professional/artistic duties, or incomes due for an obligation to act, not to act, or to allow - that do not require being registered to the "Gestione separata"'),
    ('O1', '[O1] Incomes due for an obligation to act, not to act, or to allow - that do not require being registered to the "Gestione Separata"'),
    ('P', '[P] Compensation for people residing abroad for continuous use or concession of industrial machinery, commercial or scientific tools that are on the Italian soil'),
    ('Q', '[Q] Provisions for exclusive agents or sales representatives\' work'),
    ('R', '[R] Provisions for non-exclusive agents or sales representatives\' work'),
    ('S', '[S] Provisions for commissioner work'),
    ('T', '[T] Provisions for mediator work'),
    ('U', '[U] Provisions for procurer work'),
    ('V', '[V] Provisions for door-to-door sales persons and newspaper selling in kiosks'),
    ('V1', '[V1] Income from unusual commercial activities (such as provisions for occasional work or sales representative, mediator, procurer)'),
    ('V2', '[V2] Income from unusual work activities from door-to-door sales representatives'),
    ('W', '[W] Income from 2015 tinders subject to law art. 25-ter D.P.R. 600/1973'),
    ('X', '[X] Income from 2014 for foreign companies or institutions subject to law art. 26-quater, c. 1, lett. a) and b) D.P.R. 600/1973'),
    ('Y', '[Y] Income from 1.01.2005 to 26.07.2005 from companies or institutions not included in the description above'),
    ('Z', '[Z] Deprecated'),
    ('ZO', '[ZO] Other reason'),
]

PENSION_FUND_TYPE_SELECTION = [
    ('TC01', 'National pension fund for lawyers and solicitors'),
    ('TC02', 'Pension fund for accountants with a degree'),
    ('TC03', 'Pension fund for surveyors'),
    ('TC04', 'National pension fund for associated engineers and architects'),
    ('TC05', 'National pension fund for notaries'),
    ('TC06', 'Pension fund for accountants without a degree and commercial experts'),
    ('TC07', 'ENASARCO pension fund for sales agents'),
    ('TC08', 'ENPACL pension fund for labor consultants'),
    ('TC09', 'ENPAM pension fund for doctors'),
    ('TC10', 'ENPAF pension fund for chemists'),
    ('TC11', 'ENPAV pension fund for veterinaries'),
    ('TC12', 'ENPAIA pension fund for people working in agriculture'),
    ('TC13', 'Pension fund for employees in delivery and marine agencies'),
    ('TC14', 'INPGI pension fund for journalists'),
    ('TC15', 'ONAOSI fund for sanitary orphans'),
    ('TC16', 'CASAGIT Additional pension fund for journalists'),
    ('TC17', 'EPPI pension fund for industrial experts'),
    ('TC18', 'EPAP pension fund'),
    ('TC19', 'ENPAB national pension fund for biologists'),
    ('TC20', 'ENPAPI national pension fund for nurses'),
    ('TC21', 'ENPAP national pension fund for psychologists'),
    ('TC22', 'INPS national pension fund'),
]


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_it_withholding_type = fields.Selection(WITHHOLDING_TYPE_SELECTION, string="Withholding tax type (Italy)", help="Withholding tax type. Only for Italian accounting EDI.")
    l10n_it_withholding_reason = fields.Selection(WITHHOLDING_REASON_SELECTION, string="Withholding tax reason (Italy)", help="Withholding tax reason. Only for Italian accounting EDI.")
    l10n_it_pension_fund_type = fields.Selection(PENSION_FUND_TYPE_SELECTION, string="Pension fund type (Italy)", help="Pension Fund Type. Only for Italian accounting EDI.")

    def _l10n_it_filter_kind(self, kind):
        # EXTENDS l10n_it_edi
        match kind:
            case 'withholding':
                return self.filtered(lambda tax: tax.l10n_it_withholding_type)
            case 'withholding_no_enasarco':
                # Enasarco has both withholding and pension fund types,
                # but it must be considered a pension fund for the checks.
                return self.filtered(lambda tax:
                    tax.l10n_it_withholding_type
                    and tax.l10n_it_withholding_type != 'RT04'
                )
            case 'pension_fund':
                return self.filtered(lambda tax: tax.l10n_it_pension_fund_type)
            case 'vat':
                return super()._l10n_it_filter_kind('vat').filtered(lambda tax:
                    not tax.l10n_it_withholding_type
                    and not tax.l10n_it_pension_fund_type
                )
            case _:
                return super()._l10n_it_filter_kind(kind)

    @api.onchange("l10n_it_withholding_type")
    def _onchange_l10n_it_withholding_type(self):
        """ When no withholding type is selected, there should be no withholding reason, the field is hidden """
        taxes_to_be_cleared = self.filtered(lambda tax: tax.l10n_it_withholding_reason and not tax.l10n_it_withholding_type)
        taxes_to_be_cleared.l10n_it_withholding_reason = False

    @api.constrains('amount', 'l10n_it_withholding_type', 'l10n_it_withholding_reason', 'l10n_it_pension_fund_type')
    def _validate_withholding(self):
        for tax in self:
            if tax.l10n_it_withholding_type and tax.amount >= 0:
                raise ValidationError(_("Tax '%s' has a withholding type so the amount must be negative.", tax.name))
            if tax.l10n_it_withholding_type and not tax.l10n_it_withholding_reason:
                raise ValidationError(_("Tax '%s' has a withholding type, so the withholding reason must also be specified", tax.name))
            if tax.l10n_it_withholding_reason and not tax.l10n_it_withholding_type:
                raise ValidationError(_("Tax '%s' has a withholding reason, so the withholding type must also be specified", tax.name))
            if (tax.l10n_it_withholding_type == 'RT04') ^ (tax.l10n_it_pension_fund_type == 'TC07'):
                raise ValidationError(_("Tax '%s' has one of withholding and pension fund types that do not relate to ENASARCO, and one that does.", tax.name))
            if tax.l10n_it_withholding_type == 'RT04' and tax.l10n_it_withholding_reason != 'ZO':
                raise ValidationError(_("Tax '%s' has withholding type ENASARCO, the withholding reason should be [ZO] - Other reason.", tax.name))
