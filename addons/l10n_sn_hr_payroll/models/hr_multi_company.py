# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
import logging

_logger = logging.getLogger(__name__)


class HrSalaryCategoryMultiCompany(models.Model):
    """inherit model for removing required=True for company field """
    _inherit = 'hr.salary.rule.category'

    company_id = fields.Many2one('res.company', 'Compagnie', copy=False,
                                 default=lambda self: self.env.company)


class OptesisConventionInherit(models.Model):
    """inherit model for adding company_id field"""
    _inherit = "optesis.convention"

    company_id = fields.Many2one('res.company', 'Compagnie', copy=False, readonly=True,
                                 default=lambda self: self.env.company)


class OptesisLineConvention(models.Model):
    """inherit model for adding company_id field"""
    _inherit = "line.optesis.convention"

    company_id = fields.Many2one('res.company', 'Compagnie', copy=False, readonly=True,
                                 default=lambda self: self.env.company)


class HRPayrollStructureMulticompany(models.Model):
    """inherit model for removing required=True for company field """
    _inherit = "hr.payroll.structure"

    company_id = fields.Many2one('res.company', 'Compagnie', required=False)

    
    @api.model
    def _get_default_rule_ids(self):
        return [
            (0, 0, {
                'name': 'Salaire de base',
                'sequence': 1000,
                'code': 'C1000',
                'category_id': self.env.ref('hr_payroll.BASIC').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = contract.wage*(worked_days.WORK100.number_of_days)/30',
                'note': 'La règle du salaire de base',
            }),
            (0, 0, {
                'name': 'Allocation Congés',
                'sequence': 1060,
                'code': 'C1060',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'python',
                'condition_python': """if contract.alloc_conges != 0:
                    result = True""",
                'amount_select': 'code',
                'amount_python_compute': 'result = round(contract.alloc_conges)',
            }),
            (0, 0, {
                'name': 'Prime de transport',
                'sequence': 1125,
                'code': 'C1125',
                'category_id': self.env.ref('l10n_sn_hr_payroll.non_imposable').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = worked_days.WORK100.number_of_days*20800/30',
                'note': 'Prime de transport',
            }),
            (0, 0, {
                'name': 'Indemnité KM',
                'sequence': 1140,
                'code': 'C1100',
                'category_id': self.env.ref('l10n_sn_hr_payroll.non_imposable').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = worked_days.WORK100.number_of_days*50000/30',
                'note': 'Indemnité KM',
            }),
            (0, 0, {
                'name': 'Salaire Brut',
                'sequence': 1148,
                'code': 'C1148',
                'category_id': self.env.ref('hr_payroll.GROSS').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = round(categories.BASE + categories.INDM + categories.NOIMP + categories.HS)',
                'note': 'la valeur du salaire Brut se base sur la somme du salaire de base et les indemnités tout en faisant la soustraction des déductions.',
                'appears_on_payslip': True
            }),
            (0, 0, {
                'name': 'Ipres RG',
                'sequence': 2030,
                'code': 'C2030',
                'category_id': self.env.ref('l10n_sn_hr_payroll.SALC').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'min((categories.BRUT - categories.NOIMP),360000)',
                'quantity': 1,
                'amount_percentage': 5.6,
                'note': 'Ipres RG',
                'partner_id': self.env.ref('l10n_sn_hr_payroll.hr_prevoyance_register').id
            }),
            (0, 0, {
                'name': 'Ipres RG Pat',
                'sequence': 2031,
                'code': 'C2031',
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'min((categories.BRUT - categories.NOIMP),360000)',
                'quantity': 1,
                'amount_percentage': 5.6,
                'note': 'Ipres RG',
                'partner_id': self.env.ref('l10n_sn_hr_payroll.hr_prevoyance_register').id
            }),
            (0, 0, {
                'name': 'Ipres RC',
                'sequence': 2040,
                'code': 'C2040',
                'category_id': self.env.ref('l10n_sn_hr_payroll.SALC').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'min(categories.BRUT - categories.NOIMP,1080000)',
                'quantity': 1,
                'amount_percentage': 2.4,
                'note': 'Ipres RC',
                'partner_id': self.env.ref('l10n_sn_hr_payroll.hr_prevoyance_register').id
            }),
            (0, 0, {
                'name': 'Ipres RC Pat',
                'sequence': 2041,
                'code': 'C2041',
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'min(categories.BRUT - categories.NOIMP,1080000)',
                'quantity': 1,
                'amount_percentage': 3.6,
                'note': 'Ipres RC Patronale',
                'partner_id': self.env.ref('l10n_sn_hr_payroll.hr_prevoyance_register').id
            }),
            (0, 0, {
                'name': 'Prestations Familiale',
                'sequence': 2010,
                'code': 'C2010',
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'min(63000,categories.BRUT)',
                'quantity': 1,
                'amount_percentage': 7,
            }),
            (0, 0, {
                'name': 'Accident de travail',
                'sequence': 2020,
                'code': 'C2020',
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'min(63000,categories.BRUT)',
                'quantity': 1,
                'amount_percentage': 7,
                'note': """C'est la valeur d'accident de travail qui se base sur la valeur de salaire "Brut". Elle doit être réglée chaque trimestre .Cette valeur appartient à la rubrique "Cotisations Patronales"""
            }),
            (0, 0, {
                'name': 'CFCE',
                'sequence': 2000,
                'code': 'C2000',
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'categories.BRUT - categories.NOIMP',
                'quantity': 1,
                'amount_percentage': 3,
                'partner_id': self.env.ref('l10n_sn_hr_payroll.hr_VRS_register').id
            }),
            (0, 0, {
                'name': 'Total Charges Patronales',
                'sequence': 3010,
                'code': 'C3010',
                'category_id': self.env.ref('l10n_sn_hr_payroll.TOTALCOMP').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = round(categories.COMP)',
                'note': """la somme des charges patronales."""
            }),
            (0, 0, {
                'name': """Cout total pour l'entreprise""",
                'sequence': 3020,
                'code': 'C3020',
                'category_id': self.env.ref('l10n_sn_hr_payroll.TOTAL').id,
                'appears_on_payslip': True,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = round(categories.BRUT + categories.COMP)',
                'note': """le coût total de l'entreprise qui est la somme du salaire brut et les cotistaions patronales."""
            }),
            (0, 0, {
                'name': '2eme Tranche',
                'sequence': 2100,
                'code': 'C2100',
                'category_id': self.env.ref('l10n_sn_hr_payroll.tranche_impot_sur_revenu').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if categories.BFISC < 125000 and categories.BFISC > 52500:
  result=round((categories.BFISC - 52500)*0.2)
else:
  if categories.BFISC > 125000:
    result=14500
  else:
    result=0"""
            }),
            (0, 0, {
                'name': """3eme Tranche""",
                'sequence': 2101,
                'code': 'C2101',
                'category_id': self.env.ref('l10n_sn_hr_payroll.tranche_impot_sur_revenu').id,
                'appears_on_payslip': True,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if categories.BFISC < 333333 and categories.BFISC > 125000:
    result=round((categories.BFISC - 125000)*0.3)
else:
  if categories.BFISC > 333333:
    result=62500
  else:
    result=0""",
            }),
            (0, 0, {
                'name': '4eme Tranche',
                'sequence': 2102,
                'code': 'C2102',
                'category_id': self.env.ref('l10n_sn_hr_payroll.tranche_impot_sur_revenu').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if categories.BFISC < 666667 and categories.BFISC > 333333:
    result=round((categories.BFISC - 333333)*0.35)
else:
    if categories.BFISC > 666667 :
      result=116667
    else:
      result=0""",
            }),
            (0, 0, {
                'name': '5eme Tranche',
                'sequence': 2103,
                'code': 'C2103',
                'category_id': self.env.ref('l10n_sn_hr_payroll.tranche_impot_sur_revenu').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if categories.BFISC <= 1125000 and categories.BFISC > 666667:
    result=round((categories.BFISC - 666667)*0.37)
else:
    if categories.BFISC > 1125000:
      result=169583
    else:
      result=0""",
            }),
            (0, 0, {
                'name': '6eme Tranche',
                'sequence': 2104,
                'code': 'C2104',
                'category_id': self.env.ref('l10n_sn_hr_payroll.tranche_impot_sur_revenu').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if categories.BFISC > 1125000:
    result=round((categories.BFISC - 1125000)*0.4)
else:
    result=0""",
            }),
            (0, 0, {
                'name': 'Base fiscal après abattement',
                'sequence': 1210,
                'code': 'C1210',
                'category_id': self.env.ref('l10n_sn_hr_payroll.base_fiscal').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """abattement = min(categories.C_IMP*0.3, 75000)
result = categories.C_IMP - abattement""",
            }),
            (0, 0, {
                'name': 'Réduction 1',
                'sequence': 2120,
                'code': 'C2120',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 1.5:
  if (categories.CTIR*0.1) < 8333:
     result = 8333
  elif (categories.CTIR*0.1) > 25000:
    result = 25000
  else:
    result = round(categories.CTIR*0.1)
else:
   result = 0""",
            }),
            (0, 0, {
                'name': 'Réduction 2',
                'sequence': 2121,
                'code': 'C2121',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 2:
  if (categories.CTIR*0.15) < 16666.66666666667:
    result = 16666.66666666667
  elif (categories.CTIR*0.15) > 54166.66666666667:
    result = 54166.66666666667
  else:
    result = categories.CTIR*0.15
else:
  result=0""",
            }),
            (0, 0, {
                'name': 'Réduction 3',
                'sequence': 2122,
                'code': 'C2122',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 2.5:
  if (categories.CTIR*0.2) < 25000:
    result = 25000
  elif (categories.CTIR*0.2) > 91666.66666666667:
    result = 91666.66666666667
  else:
    result = categories.CTIR*0.2
else:
  result=0""",
            }),
            (0, 0, {
                'name': 'Réduction 4',
                'sequence': 2123,
                'code': 'C2123',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 3:
  if (categories.CTIR*0.25) < 33333.33333333333:
    result = 33333.33333333333
  elif (categories.CTIR*0.25) > 137500:
    result = 137500
  else:
    result = categories.CTIR*0.25
else:
  result=0""",
            }),
            (0, 0, {
                'name': 'Réduction 5',
                'sequence': 2124,
                'code': 'C2124',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 3.5:
  if (categories.CTIR*0.3) < 41666.66666666667:
    result = 41666.66666666667
  elif (categories.CTIR*0.3) > 169166.6666666667:
    result = 169166.6666666667
  else:
    result = categories.CTIR*0.3
else:
  result=0""",
            }),
            (0, 0, {
                'name': 'Réduction 6',
                'sequence': 2125,
                'code': 'C2125',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 4:
  if (categories.CTIR*0.35) < 50000:
    result = 50000
  elif (categories.CTIR*0.35) > 207500:
    result = 207500
  else:
    result = categories.CTIR*0.35
else:
  result = 0""",
            }),
            (0, 0, {
                'name': 'Réduction 7',
                'sequence': 2126,
                'code': 'C2126',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 4.5:
  if (categories.CTIR*0.4) < 58333.33333:
    result = 58333.33333
  elif (categories.CTIR*0.4) > 229583.3333:
    result = 229583.3333
  else:
    result = categories.CTIR*0.4
else:
  result = 0""",
            }),
            (0, 0, {
                'name': 'Réduction 8',
                'sequence': 2127,
                'code': 'C2127',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if employee.ir == 5:
  if (categories.CTIR*0.45) < 66666.66667:
    result = 66666.66667
  elif (categories.CTIR*0.45) > 265000:
    result = 265000
  else:
    result = categories.CTIR*0.45
else:
  result = 0""",
            }),
            (0, 0, {
                'name': 'IR',
                'sequence': 2140,
                'code': 'C2140',
                'category_id': self.env.ref('l10n_sn_hr_payroll.impot_sur_revenu').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if (categories.TIR - categories.CRED) > 0:
  result = round(categories.TIR - categories.CRED)
else:
  result=0""",
            }),
            (0, 0, {
                'name': """Total Déductions d'impôt""",
                'sequence': 2130,
                'code': 'C2130',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPPS').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """if categories.DEDIRPP < 0:
  result=0
else:
  result = round(categories.DEDIRPP)""",
                'note': """Cette règle représente la somme de toutes les déductions d'impôt que le salarié peut subir."""
            }),
            (0, 0, {
                'name': """Trimf""",
                'sequence': 2050,
                'code': 'C2050',
                'category_id': self.env.ref('hr_payroll.DED').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if payslip.date_from.month != 12:
  result = True
else:
  if employee.payslip_count > 11:
      result = False
  else:
      result = True""",
                'amount_select': 'code',
                'amount_python_compute': """if categories.C_IMP < 50000:
  result = employee.trimf*75
else:
  if categories.C_IMP < 83333:
    result = employee.trimf*300
  else:
    if categories.C_IMP < 166667:
      result = employee.trimf*400
    else:
      if categories.C_IMP < 583334:
        result = employee.trimf*1000
      else:
        if categories.C_IMP < 1000000:
          result = employee.trimf*1500
        else:
          result = employee.trimf*3000""",
                'partner_id': self.env.ref('l10n_sn_hr_payroll.hr_VRS_register').id
            }),
            (0, 0, {
                'name': """Total Retenues""",
                'sequence': 3000,
                'code': 'C3000',
                'category_id': self.env.ref('l10n_sn_hr_payroll.DEDIRPPS').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """result = round(categories.DED+categories.SALC+categories.IR)""",
                'note': """Cette règle mais en valeur la somme de toutes les retenues."""
            }),
            (0, 0, {
                'name': """Net""",
                'sequence': 5000,
                'code': 'C5000',
                'category_id': self.env.ref('hr_payroll.NET').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """result = round(categories.BRUT - categories.DED - categories.SALC)""",
                'note': """C'est le salaire Net qui est le salaire Brut - toutes les retenues."""
            }),
            (0, 0, {
                'name': """IR REGUL""",
                'sequence': 2160,
                'code': 'C2160',
                'category_id': self.env.ref('l10n_sn_hr_payroll.impot_sur_revenu').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if payslip.date_from.month != 12:
    result = True
else:
    if employee.payslip_count > 11:
        result = False
    else:
        result = True""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00,
                'note': """C'est le regule de l'IR """
            }),
            (0, 0, {
                'name': """IR RECAL""",
                'sequence': 2150,
                'code': 'C2150',
                'category_id': self.env.ref('l10n_sn_hr_payroll.impot_sur_revenu').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if payslip.date_from.month != 12:
    result = True
else:
    if employee.payslip_count > 11:
        result = False
    else:
        result = True""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00,
                'note': """C'est l'IR recalculé """
            }),
            (0, 0, {
                'name': """SURSALAIRE""",
                'sequence': 1010,
                'code': 'C1010',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Ancienneté""",
                'sequence': 1020,
                'code': 'C1020',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """dur = payslip.date_to - contract.dateAnciennete
if dur.days > 730:
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': """dur = payslip.date_to - contract.dateAnciennete
result = round((worked_days.WORK100.number_of_days*contract.wage/30) * 0.01 * (dur.days//365))"""
            }),
            (0, 0, {
                'name': """BRUT Imposable""",
                'sequence': 1200,
                'code': 'C1200',
                'category_id': self.env.ref('l10n_sn_hr_payroll.C_IMP').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """result = categories.BRUT + categories.AVN - categories.NOIMP"""
            }),
            (0, 0, {
                'name': """Impot progressif""",
                'sequence': 2110,
                'code': 'C2110',
                'category_id': self.env.ref('l10n_sn_hr_payroll.cumul_tranche_imposable').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """result = round(categories.TIR)"""
            }),
            (0, 0, {
                'name': """RETENUE CAR PLAN""",
                'sequence': 2520,
                'code': 'C2520',
                'category_id': self.env.ref('hr_payroll.DED').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """ASSURANCE SANTE""",
                'sequence': 2500,
                'code': 'C2500',
                'category_id': self.env.ref('hr_payroll.DED').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'quantity': 1,
                'amount_fix': 7700.00
            }),
            (0, 0, {
                'name': """ASSURANCE SANTE""",
                'sequence': 2500,
                'code': 'C2500',
                'category_id': self.env.ref('hr_payroll.DED').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'quantity': 1,
                'amount_fix': 7700.00
            }),
            (0, 0, {
                'name': """Avance tabaski""",
                'sequence': 1070,
                'code': 'C1070',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'appears_on_payslip': False,
                'amount_select': 'fix',
                'condition_select': 'none',
                'quantity': 1,
                'amount_fix': 15000.00
            }),
            (0, 0, {
                'name': 'Retraite complémentaire',
                'sequence': 2042,
                'code': 'C2042',
                'category_id': self.env.ref('l10n_sn_hr_payroll.SALC').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'categories.C_IMP',
                'quantity': 1,
                'amount_percentage': 3.33
            }),
            (0, 0, {
                'name': 'Retraite complémentaire Pat',
                'sequence': 2043,
                'code': 'C2043',
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'condition_select': 'none',
                'amount_select': 'percentage',
                'amount_percentage_base': 'categories.C_IMP',
                'quantity': 1,
                'amount_percentage': 6.67
            }),
            (0, 0, {
                'name': """Prime  de logement""",
                'sequence': 1030,
                'code': 'C1030',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'appears_on_payslip': False,
                'amount_select': 'fix',
                'condition_select': 'none',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Provision retraite""",
                'sequence': 1147,
                'code': 'C1147',
                'category_id': self.env.ref('l10n_sn_hr_payroll.provision').id,
                'appears_on_payslip': False,
                'amount_select': 'fix',
                'condition_select': 'none',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Indemnité retraite""",
                'sequence': 1120,
                'code': 'C1120',
                'category_id': self.env.ref('l10n_sn_hr_payroll.provision').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if contract.motif and contract.motif == 'retraite':
  result = True""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Provision Fin de contrat""",
                'sequence': 1160,
                'code': 'C1160',
                'category_id': self.env.ref('l10n_sn_hr_payroll.provision').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if contract.date_end and not contract.motif:
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': 'result = round(C1148*7/100)'
            }),
            (0, 0, {
                'name': """Indemnité Fin de contrat""",
                'sequence': 1131,
                'code': 'C1131',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if contract.motif and contract.motif == 'fin':
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': """result = round(contract.cumul_provision_fin_contrat + (categories.BASE + categories.INDM + categories.NOIMP)*7/100)"""
            }),
            (0, 0, {
                'name': """Indemnité de licenciement""",
                'sequence': 1145,
                'code': 'C1145',
                'category_id': self.env.ref('l10n_sn_hr_payroll.non_imposable').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if contract.motif and contract.motif == 'licenciement':
  result = True""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Indemnité de décès""",
                'sequence': 1146,
                'code': 'C1146',
                'category_id': self.env.ref('l10n_sn_hr_payroll.non_imposable').id,
                'appears_on_payslip': False,
                'condition_select': 'python',
                'condition_python': """if contract.motif and contract.motif == 'deces':
  result = True""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Provision congés""",
                'sequence': 1150,
                'code': 'C1150',
                'category_id': self.env.ref('l10n_sn_hr_payroll.provision').id,
                'appears_on_payslip': False,
                'amount_select': 'code',
                'condition_select': 'python',
                'condition_python': """if contract.alloc_conges != 0:
  result = True""",
                'amount_python_compute': """result= round((categories.BASE+categories.INDM - C1060)/12)"""
            }),
            (0, 0, {
                'name': """Prime 13ème Mois""",
                'sequence': 1015,
                'code': 'C1015',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'appears_on_payslip': False,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': """year = ''
nbj = payslip.env['hr.payslip'].get_worked_days_per_year(employee.id,year)
result =(nbj/365)*categories.BASE + C1010 if nbj != 0 else 0""",
                'note': 'Prime 13ème Mois'
            }),
            (0, 0, {
                'name': """HS 15%""",
                'active': False,
                'sequence': 1021,
                'code': 'HS15',
                'category_id': self.env.ref('l10n_sn_hr_payroll.hs').id,
                'appears_on_payslip': True,
                'condition_select': 'python',
                'condition_python': """if inputs.HS15.amount !=0:
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': """result = inputs.HS15.amount*1.15*(categories.BASE + categories.INDM)/173.3333"""
            }),
            (0, 0, {
                'name': """HS 40%""",
                'active': False,
                'sequence': 1022,
                'code': 'HS40',
                'category_id': self.env.ref('l10n_sn_hr_payroll.hs').id,
                'appears_on_payslip': True,
                'condition_select': 'python',
                'condition_python': """if inputs.HS40.amount !=0:
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': """result = inputs.HS40.amount*1.4*(categories.BASE + categories.INDM)/173.3333"""
            }),
            (0, 0, {
                'name': """HS 60%""",
                'active': False,
                'sequence': 1023,
                'code': 'HS60',
                'category_id': self.env.ref('l10n_sn_hr_payroll.hs').id,
                'appears_on_payslip': True,
                'condition_select': 'python',
                'condition_python': """if inputs.HS60.amount !=0:
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': """result = inputs.HS60.amount*1.6*(categories.BASE + categories.INDM)/173.3333"""
            }),
            (0, 0, {
                'name': """HS 100%""",
                'active': False,
                'sequence': 1024,
                'code': 'HS100',
                'category_id': self.env.ref('l10n_sn_hr_payroll.hs').id,
                'appears_on_payslip': True,
                'condition_select': 'python',
                'condition_python': """if inputs.HS100.amount !=0:
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': """result = inputs.HS100.amount*2*(categories.BASE + categories.INDM)/173.3333"""
            }),
            (0, 0, {
                'name': """Soldes conges""",
                'sequence': 1051,
                'code': 'C1051',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'python',
                'condition_python': """if contract.motif:
  result = True""",
                'amount_select': 'code',
                'amount_python_compute': """result = contract.cumul_mensuel"""
            }),
            (0, 0, {
                'name': """Avantages en nature""",
                'sequence': 1090,
                'code': 'C1090',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """IR ANNUEL""",
                'sequence': 2161,
                'code': 'C2161',
                'category_id': self.env.ref('l10n_sn_hr_payroll.impot_sur_revenu').id,
                'condition_select': 'python',
                'condition_python': """if employee.payslip_count > 11 and payslip.date_from.month == 12:
  result = True
else:
  result = False""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """CUMUL IR""",
                'sequence': 2162,
                'code': 'C2162',
                'category_id': self.env.ref('l10n_sn_hr_payroll.impot_sur_revenu').id,
                'condition_select': 'python',
                'condition_python': """if employee.payslip_count > 11 and payslip.date_from.month == 12:
  result = True
else:
  result = False""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """REGUL IR ANNUEL""",
                'sequence': 2163,
                'code': 'C2163',
                'category_id': self.env.ref('l10n_sn_hr_payroll.impot_sur_revenu').id,
                'condition_select': 'python',
                'condition_python': """if employee.payslip_count > 11 and payslip.date_from.month == 12:
  result = True
else:
  result = False""",
                'amount_select': 'code',
                'amount_python_compute': """result = C2162 - C2161""",
            }),
            (0, 0, {
                'name': """Cumul Trimf""",
                'sequence': 2047,
                'code': 'C2047',
                'category_id': self.env.ref('l10n_sn_hr_payroll.trimf').id,
                'condition_select': 'python',
                'condition_python': """if employee.payslip_count > 11 and payslip.date_from.month == 12:
  result = True
else:
  result = False""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Trimf Annuelle""",
                'sequence': 2048,
                'code': 'C2048',
                'category_id': self.env.ref('l10n_sn_hr_payroll.trimf').id,
                'condition_select': 'python',
                'condition_python': """if employee.payslip_count > 11 and payslip.date_from.month == 12:
  result = True
else:
  result = False""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Regul Trimf""",
                'sequence': 2048,
                'code': 'C2048',
                'category_id': self.env.ref('l10n_sn_hr_payroll.trimf').id,
                'condition_select': 'python',
                'condition_python': """if employee.payslip_count > 11 and payslip.date_from.month == 12:
  result = True
else:
  result = False""",
                'amount_select': 'fix',
                'quantity': 1,
                'amount_fix': 0.00
            }),
            (0, 0, {
                'name': """Trimf""",
                'sequence': 2050,
                'code': 'C2050',
                'category_id': self.env.ref('hr_payroll.DED').id,
                'condition_select': 'python',
                'condition_python': """if employee.payslip_count > 11 and payslip.date_from.month == 12:
  result = True
else:
  result = False""",
                'amount_select': 'code',
                'amount_python_compute': """trimf_val = 0
if categories.C_IMP < 50000:
  trimf_val = employee.trimf*75
else:
  if categories.C_IMP < 83333:
    trimf_val = employee.trimf*300
  else:
    if categories.C_IMP < 166667:
      trimf_val = employee.trimf*400
    else:
      if categories.C_IMP < 583334:
        trimf_val = employee.trimf*1000
      else:
        if categories.C_IMP < 1000000:
          trimf_val = employee.trimf*1500
        else:
          trimf_val = employee.trimf*3000
result = trimf_val - C2049""",
                'partner_id': self.env.ref('l10n_sn_hr_payroll.hr_VRS_register').id
            }),
            
        ]
    
    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules', default=_get_default_rule_ids)


class HRAccountJournal(models.Model):
    """inherit model for removing required=True for company field """
    _inherit = "account.journal"

    company_id = fields.Many2one('res.company', 'Compagnie',  required=False)
    
    
    
class HRSalaryRuleInherit(models.Model):
    """inherit model to add company_id"""
    _inherit = "hr.salary.rule"

    company_id = fields.Many2one('res.company', 'Compagnie', required=False)
    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure", required=False, ondelete="cascade")
    
    
class HRSalaryRuleTypeInherit(models.Model):
    """inherit model to add company_id"""
    _inherit = "hr.payroll.structure.type"

    company_id = fields.Many2one('res.company', 'Compagnie',  required=False)
    
    
class HRSalaryRuleTypeInherit(models.Model):
    """inherit model to add company_id"""
    _inherit = "hr.payslip.input.type"

    company_id = fields.Many2one('res.company', 'Compagnie',  required=False)
