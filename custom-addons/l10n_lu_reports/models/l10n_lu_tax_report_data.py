# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Mandatory fields
VAT_MANDATORY_FIELDS = {
    '012', '013', '014', '018', '021', '022', '037',
    '046', '051', '056', '065', '076', '102', '103',
    '104', '105', '152', '233', '234', '235', '236',
    '361', '362', '407', '409', '410', '419', '423',
    '436', '462', '463', '464', '765', '766', '767',
    '768',
    # Simplified-only
    '450', '801', '802',
    # Monthly-only
    '093', '097', '457',
    # 033 and 042 are mandatory when 403 is specified (always true for us, with 0% tax)
    '033', '042', '403', '414', '415', '418', '416',
    '417', '453', '452', '451',
}

# Mapping dictionary: monthly fields as keys, list of corresponding annual fields as values
YEARLY_MONTHLY_FIELDS_TO_DELETE = [
    '472', '455', '456', '457', '458', '459', '460', '461', '454'
]

# Fields of the annual simplified declaration
# List drawn from : https://ecdf-developer.b2g.etat.lu/ecdf/formdocs/2020/TVA_DECAS/2020M1V002/TVA_DECAS_LINK_10_DOC_FR_2020M1V002.fieldlist
# PLUS the date fields
YEARLY_SIMPLIFIED_FIELDS = [
    '233', '234', '235', '236',
    '012', '471', '481', '450', '423', '424', '801', '802', '805', '806',
    '807', '808', '819', '820', '817', '818', '051', '056', '711', '712',
    '713', '714', '715', '716', '049', '054', '194', '065', '407', '721',
    '722', '723', '724', '725', '726', '059', '068', '195', '731', '732',
    '733', '734', '735', '736', '063', '073', '196', '409', '410', '436',
    '462', '741', '742', '743', '744', '745', '746', '431', '432', '435',
    '463', '464', '751', '752', '753', '754', '755', '756', '441', '442',
    '445', '765', '766', '761', '762', '767', '768', '763', '764', '076',
    '911', '912', '913', '914', '915', '916', '921', '922', '923', '924',
    '925', '926', '931', '932', '933', '934', '935', '936', '941', '942',
    '943', '944', '945', '946', '951', '952', '953', '954', '955', '956',
    '961', '962', '963', '964', '769', '770',
]

# New total fields in the simplified declaration
YEARLY_SIMPLIFIED_NEW_TOTALS = {
    '450': ['423', '424'],
    '481': ['472', '455', '456'],
    '076': ['802', '056', '407', '410', '768']
}

# mapping multi-column lines to correct fields, because expressions don't have codes
MULTI_COLUMN_FIELDS = {
    '192': {'vat_excluded': '192', 'vat_invoiced': '193'},
    '239': {'total': '239', 'percent': '240', 'vat_excluded': '114'},
    '241': {'total': '241', 'percent': '242', 'vat_excluded': '243'},
    '244': {'total': '244', 'percent': '245', 'vat_excluded': '246'},
    '247': {'total': '247', 'percent': '248', 'vat_excluded': '249'},
    '250': {'total': '250', 'percent': '251', 'vat_excluded': '252'},
    '253': {'total': '253', 'percent': '254', 'vat_excluded': '255'},
    '256': {'total': '256', 'percent': '257', 'vat_excluded': '258', 'vat_invoiced': '259'},
    '260': {'total': '260', 'percent': '261', 'vat_excluded': '262', 'vat_invoiced': '263'},
    '265': {'total': '265', 'percent': '266', 'vat_excluded': '267', 'vat_invoiced': '268'},
    '269': {'total': '269', 'percent': '270', 'vat_excluded': '271', 'vat_invoiced': '272'},
    '274': {'total': '274', 'percent': '275', 'vat_excluded': '276', 'vat_invoiced': '277'},
    '279': {'total': '279', 'percent': '280', 'vat_excluded': '281', 'vat_invoiced': '282'},
    '283': {'total': '283', 'percent': '284', 'vat_excluded': '183', 'vat_invoiced': '184'},
    '285': {'total': '285', 'percent': '286', 'vat_excluded': '287', 'vat_invoiced': '288'},
    '289': {'total': '289', 'percent': '290', 'vat_excluded': '291', 'vat_invoiced': '292'},
    '293': {'total': '293', 'percent': '294', 'vat_excluded': '295', 'vat_invoiced': '296'},
    '297': {'total': '297', 'percent': '298', 'vat_excluded': '299', 'vat_invoiced': '300'},
    '301': {'total': '301', 'percent': '302', 'vat_excluded': '303', 'vat_invoiced': '304'},
    '305': {'total': '305', 'percent': '306', 'vat_excluded': '185', 'vat_invoiced': '186'},
    '307': {'total': '307', 'percent': '308', 'vat_excluded': '309'},
    '310': {'total': '310', 'percent': '311', 'vat_excluded': '312', 'vat_invoiced': '313'},
    '314': {'percent': '314', 'vat_excluded': '315'},
    '316': {'percent': '316', 'vat_excluded': '317'},
    '319': {'vat_excluded': '319', 'vat_invoiced': '320'},
    '322': {'vat_excluded': '322', 'vat_invoiced': '323'},
    '328': {'vat_excluded': '328', 'vat_invoiced': '329'},
    '332': {'vat_excluded': '332', 'vat_invoiced': '333'},
    '334': {'vat_excluded': '334', 'vat_invoiced': '335'},
    '337': {'vat_excluded': '337', 'vat_invoiced': '338'},
    '115': {'vat_excluded': '115', 'vat_invoiced': '187'},
    '188': {'vat_excluded': '188', 'vat_invoiced': '189'},
    '343': {'vat_excluded': '343', 'vat_invoiced': '344'},
    '345': {'vat_excluded': '345', 'vat_invoiced': '346'},
    '347': {'vat_excluded': '347', 'vat_invoiced': '348'},
    '349': {'vat_excluded': '349', 'vat_invoiced': '350'},
    '351': {'vat_excluded': '351', 'vat_invoiced': '352'},
    '353': {'vat_excluded': '353', 'vat_invoiced': '354'},
    '355': {'vat_excluded': '355', 'vat_invoiced': '356'},
    '358': {'vat_excluded': '358', 'vat_invoiced': '359'},
    '361': {'vat_excluded': '361', 'vat_invoiced': '362'},
    '190': {'vat_excluded': '190', 'vat_invoiced': '191'},
    '168': {'year_start': '168', 'year_end': '181'},
    '163': {'year_start': '163', 'year_end': '176'},
    '791': {'year_start': '791', 'year_end': '792'},
    '991': {'year_start': '991', 'year_end': '992'},
    '793': {'year_start': '793', 'year_end': '794'},
    '993': {'year_start': '993', 'year_end': '994'},
    '797': {'year_start': '797', 'year_end': '798'},
    '795': {'year_start': '795', 'year_end': '796'},
    '995': {'year_start': '995', 'year_end': '996'},
    '158': {'year_start': '158', 'year_end': '171'},
    '162': {'year_start': '162', 'year_end': '175'},
    '200': {'year_start': '200', 'year_end': '201'},
    '164': {'year_start': '164', 'year_end': '177'},
    '165': {'year_start': '165', 'year_end': '178'},
    '167': {'year_start': '167', 'year_end': '180'},
    '116': {'year_start': '116', 'year_end': '117'},
    '118': {'year_start': '118', 'year_end': '119'},
    '120': {'year_start': '120', 'year_end': '121'},
    '43': {'vat_excluded': '414', 'vat_invoiced': '415'},
}
