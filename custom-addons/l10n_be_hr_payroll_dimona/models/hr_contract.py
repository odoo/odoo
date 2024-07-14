# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import re
import string
import base64
import time
import jwt
import requests

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import timedelta
from werkzeug.urls import url_quote

from odoo import api, fields, models, _
from odoo.exceptions import UserError

AUTH_ENDPOINT = 'https://services.socialsecurity.be/REST/oauth/v3/token'
POST_ENDPOINT = 'https://services.socialsecurity.be/REST/dimona/v1/declarations'

DIMONA_TIMEOUT = 10

ONSS_COUNTRY_CODE_MAPPING = {
    'AD': '00102', 'AE': '00260', 'AF': '00251', 'AG': '00403', 'AI': '00490', 'AL': '00101', 'AM': '00249',
    'AO': '00341', 'AR': '00511', 'AS': '00690', 'AT': '00105', 'AU': '00611', 'AZ': '00250', 'BA': '00149',
    'BB': '00423', 'BD': '00237', 'BE': '00000', 'BF': '00308', 'BG': '00106', 'BH': '00268', 'BI': '00303',
    'BJ': '00310', 'BM': '00485', 'BN': '00224', 'BO': '00512', 'BR': '00513', 'BS': '00425', 'BT': '00223',
    'BW': '00302', 'BY': '00142', 'BZ': '00430', 'CA': '00401', 'CD': '00306', 'CF': '00305', 'CG': '00307',
    'CH': '00127', 'CI': '00309', 'CK': '00687', 'CL': '00514', 'CM': '00304', 'CN': '00218', 'CO': '00515',
    'CR': '00411', 'CU': '00412', 'CV': '00339', 'CY': '00107', 'CZ': '00140', 'DE': '00103', 'DJ': '00345',
    'DK': '00108', 'DM': '00480', 'DO': '00427', 'DZ': '00351', 'EC': '00516', 'EE': '00136', 'EG': '00352',
    'EH': '00388', 'ER': '00349', 'ES': '00109', 'ET': '00311', 'FI': '00110', 'FJ': '00617', 'FK': '00580',
    'FM': '00602', 'FR': '00111', 'GA': '00312', 'GB': '00112', 'GD': '00426', 'GE': '00253', 'GF': '00581',
    'GH': '00314', 'GI': '00180', 'GL': '00498', 'GM': '00313', 'GN': '00315', 'GP': '00496', 'GQ': '00337',
    'GR': '00114', 'GT': '00413', 'GU': '00681', 'GW': '00338', 'GY': '00521', 'HK': '00234', 'HN': '00414',
    'HR': '00146', 'HT': '00419', 'HU': '00115', 'ID': '00208', 'IE': '00116', 'IL': '00256', 'IN': '00207',
    'IQ': '00254', 'IR': '00255', 'IS': '00117', 'IT': '00128', 'JM': '00415', 'JO': '00257', 'JP': '00209',
    'KE': '00336', 'KG': '00226', 'KH': '00216', 'KI': '00622', 'KM': '00343', 'KN': '00431', 'KP': '00219',
    'KR': '00206', 'KW': '00264', 'KY': '00492', 'KZ': '00225', 'LA': '00210', 'LB': '00258', 'LC': '00428',
    'LI': '00118', 'LK': '00203', 'LR': '00318', 'LS': '00301', 'LT': '00137', 'LU': '00113', 'LV': '00135',
    'LY': '00353', 'MA': '00354', 'MC': '00120', 'MD': '00144', 'ME': '00151', 'MG': '00324', 'MH': '00603',
    'MK': '00148', 'ML': '00319', 'MM': '00201', 'MN': '00221', 'MO': '00281', 'MQ': '00497', 'MR': '00355',
    'MS': '00493', 'MT': '00119', 'MU': '00317', 'MV': '00222', 'MW': '00358', 'MX': '00416', 'MY': '00212',
    'MZ': '00340', 'NA': '00384', 'NC': '00683', 'NE': '00321', 'NG': '00322', 'NI': '00417', 'NL': '00129',
    'NO': '00121', 'NP': '00213', 'NR': '00615', 'NU': '00604', 'NZ': '00613', 'OM': '00266', 'PA': '00418',
    'PE': '00518', 'PF': '00684', 'PG': '00619', 'PH': '00214', 'PK': '00259', 'PL': '00122', 'PM': '00495',
    'PN': '00692', 'PR': '00487', 'PS': '00271', 'PT': '00123', 'PW': '00679', 'PY': '00517', 'QA': '00267',
    'RE': '00387', 'RO': '00124', 'RS': '00152', 'RU': '00145', 'RW': '00327', 'SA': '00252', 'SB': '00623',
    'SC': '00342', 'SD': '00356', 'SE': '00126', 'SG': '00205', 'SH': '00389', 'SI': '00147', 'SK': '00141',
    'SL': '00328', 'SM': '00125', 'SN': '00320', 'SO': '00329', 'SR': '00522', 'SS': '00365', 'SV': '00421',
    'SY': '00261', 'SZ': '00347', 'TC': '00488', 'TD': '00333', 'TG': '00334', 'TH': '00235', 'TJ': '00228',
    'TL': '00282', 'TM': '00229', 'TN': '00357', 'TO': '00616', 'TR': '00262', 'TT': '00422', 'TV': '00621',
    'TW': '00204', 'TZ': '00332', 'UA': '00143', 'UG': '00323', 'US': '00402', 'UY': '00519', 'UZ': '00227',
    'VA': '00133', 'VC': '00429', 'VE': '00520', 'VG': '00479', 'VI': '00478', 'VN': '00220', 'VU': '00624',
    'WF': '00689', 'WS': '00614', 'XK': '00153', 'YE': '00270', 'ZA': '00325', 'ZM': '00335', 'ZW': '00344'
}

ONSS_VALID_ZIPS = [
    '1000', '1005', '1006', '1007', '1008', '1009', '1010', '1011', '1012', '1020', '1030', '1031', '1033',
    '1035', '1040', '1041', '1043', '1044', '1045', '1046', '1047', '1048', '1049', '1050', '1060', '1070',
    '1080', '1081', '1082', '1083', '1090', '1099', '1100', '1101', '1105', '1110', '1120', '1130', '1140',
    '1150', '1160', '1170', '1180', '1190', '1200', '1201', '1210', '1212', '1300', '1301', '1310', '1315',
    '1320', '1325', '1330', '1331', '1332', '1340', '1341', '1342', '1348', '1350', '1357', '1360', '1367',
    '1370', '1380', '1390', '1400', '1401', '1402', '1404', '1410', '1414', '1420', '1421', '1428', '1430',
    '1435', '1440', '1450', '1457', '1460', '1461', '1470', '1471', '1472', '1473', '1474', '1476', '1480',
    '1490', '1495', '1500', '1501', '1502', '1540', '1541', '1547', '1560', '1570', '1600', '1601', '1602',
    '1620', '1630', '1640', '1650', '1651', '1652', '1653', '1654', '1670', '1671', '1673', '1674', '1700',
    '1701', '1702', '1703', '1730', '1731', '1733', '1740', '1741', '1742', '1745', '1750', '1755', '1760',
    '1761', '1770', '1780', '1785', '1790', '1800', '1804', '1818', '1820', '1830', '1831', '1840', '1850',
    '1851', '1852', '1853', '1860', '1861', '1880', '1910', '1930', '1931', '1932', '1933', '1934', '1935',
    '1950', '1970', '1980', '1981', '1982', '2000', '2018', '2020', '2030', '2040', '2050', '2060', '2070',
    '2075', '2099', '2100', '2110', '2140', '2150', '2160', '2170', '2180', '2200', '2220', '2221', '2222',
    '2223', '2230', '2235', '2240', '2242', '2243', '2250', '2260', '2270', '2275', '2280', '2288', '2290',
    '2300', '2310', '2320', '2321', '2322', '2323', '2328', '2330', '2340', '2350', '2360', '2370', '2380',
    '2381', '2382', '2387', '2390', '2400', '2430', '2431', '2440', '2450', '2460', '2470', '2480', '2490',
    '2491', '2500', '2520', '2530', '2531', '2540', '2547', '2550', '2560', '2570', '2580', '2590', '2600',
    '2610', '2620', '2627', '2630', '2640', '2650', '2660', '2800', '2801', '2811', '2812', '2820', '2830',
    '2840', '2845', '2850', '2860', '2861', '2870', '2880', '2890', '2900', '2910', '2920', '2930', '2940',
    '2950', '2960', '2970', '2980', '2990', '3000', '3001', '3010', '3012', '3018', '3020', '3040', '3050',
    '3051', '3052', '3053', '3054', '3060', '3061', '3070', '3071', '3078', '3080', '3090', '3110', '3111',
    '3118', '3120', '3128', '3130', '3140', '3150', '3190', '3191', '3200', '3201', '3202', '3210', '3211',
    '3212', '3220', '3221', '3270', '3271', '3272', '3290', '3293', '3294', '3300', '3320', '3321', '3350',
    '3360', '3370', '3380', '3381', '3384', '3390', '3391', '3400', '3401', '3404', '3440', '3450', '3454',
    '3460', '3461', '3470', '3471', '3472', '3473', '3500', '3501', '3510', '3511', '3512', '3520', '3530',
    '3540', '3545', '3550', '3560', '3570', '3580', '3581', '3582', '3583', '3590', '3600', '3620', '3621',
    '3630', '3631', '3640', '3650', '3660', '3665', '3668', '3670', '3680', '3690', '3700', '3717', '3720',
    '3721', '3722', '3723', '3724', '3730', '3732', '3740', '3742', '3746', '3770', '3790', '3791', '3792',
    '3793', '3798', '3800', '3803', '3806', '3830', '3831', '3832', '3840', '3850', '3870', '3890', '3891',
    '3900', '3910', '3920', '3930', '3940', '3941', '3945', '3950', '3960', '3970', '3971', '3980', '3990',
    '4000', '4020', '4030', '4031', '4032', '4040', '4041', '4042', '4050', '4051', '4052', '4053', '4075',
    '4090', '4099', '4100', '4101', '4102', '4120', '4121', '4122', '4130', '4140', '4141', '4160', '4161',
    '4162', '4163', '4170', '4171', '4180', '4181', '4190', '4210', '4217', '4218', '4219', '4250', '4252',
    '4253', '4254', '4257', '4260', '4261', '4263', '4280', '4287', '4300', '4317', '4340', '4342', '4347',
    '4350', '4351', '4357', '4360', '4367', '4400', '4420', '4430', '4431', '4432', '4450', '4451', '4452',
    '4453', '4458', '4460', '4470', '4480', '4500', '4520', '4530', '4537', '4540', '4550', '4557', '4560',
    '4570', '4577', '4590', '4600', '4601', '4602', '4606', '4607', '4608', '4610', '4620', '4621', '4623',
    '4624', '4630', '4631', '4632', '4633', '4650', '4651', '4652', '4653', '4654', '4670', '4671', '4672',
    '4680', '4681', '4682', '4683', '4684', '4690', '4700', '4701', '4710', '4711', '4720', '4721', '4728',
    '4730', '4731', '4750', '4760', '4761', '4770', '4771', '4780', '4782', '4783', '4784', '4790', '4791',
    '4800', '4801', '4802', '4820', '4821', '4830', '4831', '4834', '4837', '4840', '4841', '4845', '4850',
    '4851', '4852', '4860', '4861', '4870', '4877', '4880', '4890', '4900', '4910', '4920', '4950', '4960',
    '4970', '4980', '4983', '4987', '4990', '5000', '5001', '5002', '5003', '5004', '5010', '5012', '5020',
    '5021', '5022', '5024', '5030', '5031', '5032', '5060', '5070', '5080', '5081', '5100', '5101', '5140',
    '5150', '5170', '5190', '5300', '5310', '5330', '5332', '5333', '5334', '5336', '5340', '5350', '5351',
    '5352', '5353', '5354', '5360', '5361', '5362', '5363', '5364', '5370', '5372', '5374', '5376', '5377',
    '5380', '5500', '5501', '5502', '5503', '5504', '5520', '5521', '5522', '5523', '5524', '5530', '5537',
    '5540', '5541', '5542', '5543', '5544', '5550', '5555', '5560', '5561', '5562', '5563', '5564', '5570',
    '5571', '5572', '5573', '5574', '5575', '5576', '5580', '5590', '5600', '5620', '5621', '5630', '5640',
    '5641', '5644', '5646', '5650', '5651', '5660', '5670', '5680', '6000', '6001', '6010', '6020', '6030',
    '6031', '6032', '6040', '6041', '6042', '6043', '6044', '6060', '6061', '6075', '6099', '6110', '6111',
    '6120', '6140', '6141', '6142', '6150', '6180', '6181', '6182', '6183', '6200', '6210', '6211', '6220',
    '6221', '6222', '6223', '6224', '6230', '6238', '6240', '6250', '6280', '6440', '6441', '6460', '6461',
    '6462', '6463', '6464', '6470', '6500', '6511', '6530', '6531', '6532', '6533', '6534', '6536', '6540',
    '6542', '6543', '6560', '6567', '6590', '6591', '6592', '6593', '6594', '6596', '6600', '6630', '6637',
    '6640', '6642', '6660', '6661', '6662', '6663', '6666', '6670', '6671', '6672', '6673', '6674', '6680',
    '6681', '6686', '6687', '6688', '6690', '6692', '6698', '6700', '6704', '6706', '6717', '6720', '6721',
    '6723', '6724', '6730', '6740', '6741', '6742', '6743', '6747', '6750', '6760', '6761', '6762', '6767',
    '6769', '6780', '6781', '6782', '6790', '6791', '6792', '6800', '6810', '6811', '6812', '6813', '6820',
    '6821', '6823', '6824', '6830', '6831', '6832', '6833', '6834', '6836', '6838', '6840', '6850', '6851',
    '6852', '6853', '6856', '6860', '6870', '6880', '6887', '6890', '6900', '6920', '6921', '6922', '6924',
    '6927', '6929', '6940', '6941', '6950', '6951', '6952', '6953', '6960', '6970', '6971', '6972', '6980',
    '6982', '6983', '6984', '6986', '6987', '6990', '6997', '7000', '7010', '7011', '7012', '7020', '7021',
    '7022', '7024', '7030', '7031', '7032', '7033', '7034', '7040', '7041', '7050', '7060', '7061', '7062',
    '7063', '7070', '7080', '7090', '7100', '7110', '7120', '7130', '7131', '7133', '7134', '7140', '7141',
    '7160', '7170', '7180', '7181', '7190', '7191', '7300', '7301', '7320', '7321', '7322', '7330', '7331',
    '7332', '7333', '7334', '7340', '7350', '7370', '7380', '7382', '7387', '7390', '7500', '7501', '7502',
    '7503', '7504', '7506', '7510', '7511', '7512', '7513', '7520', '7521', '7522', '7530', '7531', '7532',
    '7533', '7534', '7536', '7538', '7540', '7542', '7543', '7548', '7600', '7601', '7602', '7603', '7604',
    '7608', '7610', '7611', '7618', '7620', '7621', '7622', '7623', '7624', '7640', '7641', '7642', '7643',
    '7700', '7711', '7712', '7730', '7740', '7742', '7743', '7750', '7760', '7780', '7781', '7782', '7783',
    '7784', '7800', '7801', '7802', '7803', '7804', '7810', '7811', '7812', '7822', '7823', '7830', '7850',
    '7860', '7861', '7862', '7863', '7864', '7866', '7870', '7880', '7890', '7900', '7901', '7903', '7904',
    '7906', '7910', '7911', '7912', '7940', '7941', '7942', '7943', '7950', '7951', '7970', '7971', '7972',
    '7973', '8000', '8020', '8200', '8210', '8211', '8300', '8301', '8310', '8340', '8370', '8377', '8380',
    '8400', '8420', '8421', '8430', '8431', '8432', '8433', '8434', '8450', '8460', '8470', '8480', '8490',
    '8500', '8501', '8510', '8511', '8520', '8530', '8531', '8540', '8550', '8551', '8552', '8553', '8554',
    '8560', '8570', '8572', '8573', '8580', '8581', '8582', '8583', '8587', '8600', '8610', '8620', '8630',
    '8640', '8647', '8650', '8660', '8670', '8680', '8690', '8691', '8700', '8710', '8720', '8730', '8740',
    '8750', '8755', '8760', '8770', '8780', '8790', '8791', '8792', '8793', '8800', '8810', '8820', '8830',
    '8840', '8850', '8851', '8860', '8870', '8880', '8890', '8900', '8902', '8904', '8906', '8908', '8920',
    '8930', '8940', '8950', '8951', '8952', '8953', '8954', '8956', '8957', '8958', '8970', '8972', '8978',
    '8980', '9000', '9030', '9031', '9032', '9040', '9041', '9042', '9050', '9051', '9052', '9060', '9070',
    '9075', '9080', '9090', '9099', '9100', '9111', '9112', '9120', '9130', '9140', '9150', '9160', '9170',
    '9180', '9185', '9190', '9200', '9220', '9230', '9240', '9250', '9255', '9260', '9270', '9280', '9290',
    '9300', '9308', '9310', '9320', '9340', '9400', '9401', '9402', '9403', '9404', '9406', '9420', '9450',
    '9451', '9470', '9472', '9473', '9500', '9506', '9520', '9521', '9550', '9551', '9552', '9570', '9571',
    '9572', '9600', '9620', '9630', '9636', '9660', '9661', '9667', '9680', '9681', '9688', '9690', '9700',
    '9750', '9770', '9771', '9772', '9790', '9800', '9810', '9820', '9830', '9831', '9840', '9850', '9860',
    '9870', '9880', '9881', '9890', '9900', '9910', '9920', '9921', '9930', '9931', '9932', '9940', '9950',
    '9960', '9961', '9968', '9970', '9971', '9980', '9981', '9982', '9988', '9990', '9991', '9992']


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_be_dimona_in_declaration_number = fields.Char(groups="hr_payroll.group_hr_payroll_user")
    l10n_be_dimona_last_declaration_number = fields.Char(groups="hr_payroll.group_hr_payroll_user")
    l10n_be_dimona_declaration_state = fields.Selection(
        selection=[
            ('none', 'Not Declared'),
            ('waiting', 'Declared and waiting status'),
            ('done', 'Declared and accepted'),
            ('done_warning', 'Declared and accepted with warnings'),
            ('refused', 'Declared and refused'),
            ('waiting_sigedis', 'Declared and waiting Sigedis'),
            ('error', "Invalid declaration or restricted access"),
        ], default='none')
    l10n_be_dimona_planned_hours = fields.Integer("Student Planned Hours")
    l10n_be_is_student = fields.Boolean(compute='_compute_l10n_be_is_student')

    # Sources:
    # https://www.socialsecurity.be/site_fr/employer/applics/dimona/introduction/webservice.htm
    # Glossary:
    # https://www.socialsecurity.be/lambda/portail/glossaires/dimona.nsf/web/glossary_home_fr
    # Rest API:
    # https://www.socialsecurity.be/site_fr/employer/applics/dimona/introduction/rest/apidoc_fr.html#/definitions/Dimona%20Out

    # The Simulation environment URLs are as follows:
    # - Dimona REST Service : https://services-sim.socialsecurity.be/REST/dimona/v1/declarations
    # - Authentication server : https://services.socialsecurity.be/REST/oauth/v3/token
    # - Audience : https://oauth.socialsecurity.be
    # The Production environment URLs are as follows :
    # - Dimona REST Service : https://services.socialsecurity.be/REST/dimona/v1/declarations
    # - Authentication server : https://services.socialsecurity.be/REST/oauth/v3/token
    # - Audience : https://oauth.socialsecurity.be

    @api.depends('structure_type_id')
    def _compute_l10n_be_is_student(self):
        student_stuct_type = self.env.ref('l10n_be_hr_payroll.structure_type_student')
        for contract in self:
            contract.l10n_be_is_student = contract.structure_type_id == student_stuct_type

    def _get_jwt(self):
        expeditor_number = self.company_id.onss_expeditor_number
        if not expeditor_number:
            raise UserError(_('No expeditor number defined on the payroll settings.'))
        pem = self.company_id.sudo().onss_pem_certificate
        passphrase = self.company_id.sudo().onss_pem_passphrase
        if passphrase:
            passphrase = passphrase.encode('utf-8')
        else:
            passphrase = None
        if not pem:
            raise UserError(_('No PEM Certificate / Passphrase defined on the Payroll Configuration'))

        pem = base64.b64decode(pem)
        private_key = serialization.load_pem_private_key(
            pem, password=passphrase, backend=default_backend())
        unique_id = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(20)])
        now = int(time.time())
        payload = {
            # Unique jwt indentifier
            "jti": unique_id,
            # App supplying the jwt
            "iss": 'self_service_expeditor_%s' % (self.company_id.onss_expeditor_number),
            # Main jwt subject
            "sub": 'self_service_expeditor_%s' % (self.company_id.onss_expeditor_number),
            # jwt receiver (audience)
            "aud": "https://oauth.socialsecurity.be",
            # Expiration
            "exp": now + 5000,
            # Timestamp before accepting jwt
            "nbf": now,
            # Creation timestamp
            "iat": now,
        }
        try:
            bearer_token = jwt.encode(payload, private_key, algorithm="RS256")
        except ValueError as e:
            raise UserError(_('Error on authentication. Please contact an administrator. (%s)', e))
        return bearer_token

    def _dimona_authenticate(self, declare=True):
        bearer = self._get_jwt()
        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'scope': 'scope:dimona:declaration:declarant' if declare else 'scope:dimona:declaration:consult',
            'client_assertion': bearer,
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        access_token = ''
        try:
            response = requests.post(AUTH_ENDPOINT, data=data, headers=headers, timeout=DIMONA_TIMEOUT)
            if response.status_code == 200:
                response_dict = response.json()
                access_token = response_dict['access_token']
            elif response.status_code == 400:
                raise UserError(_('Error with one or several invalid parameters on the POST request during authentication. Please contact an administrator. (%s)', response.text))
            elif response.status_code == 500:
                raise UserError(_('Due to a technical problem at the ONSS side, the authentication could not be done by the ONSS.'))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))
        return access_token

    def _action_open_dimona(self, foreigner=False):
        self.ensure_one()

        onss_registration_number = self.company_id.onss_registration_number
        if not onss_registration_number:
            raise UserError(_('No ONSS registration number is defined for company %s', self.company_id.name))
        niss = self.employee_id.niss
        if not foreigner and not self.employee_id._is_niss_valid():
            raise UserError(_('The NISS is invalid.'))

        first_name, last_name = self.employee_id._get_split_name()
        if not first_name or not last_name:
            raise UserError(_('The employee name is incomplete'))

        if foreigner and not all(self.employee_id[field] for field in ['birthday', 'place_of_birth', 'country_of_birth', 'country_id', 'gender']):
            raise UserError(_("Foreigner employees should provide their name, birthdate, birth place, birth country, nationality and the gender"))
        if foreigner and not all(self.employee_id[f'private_{field}'] for field in ['street', 'zip', 'city', 'country_id']):
            raise UserError(_("Foreigner employees should provide a complete address (street, number, zip, city, country"))
        if not foreigner and self.employee_id.private_zip not in ONSS_VALID_ZIPS:
            raise UserError(_("The employee zip does not exist."))

        if self.employee_id.private_street:
            street_digits = re.findall(r"[0-9]+", self.employee_id.private_street)
            if not street_digits:
                raise UserError(_('No house number found on employee street'))
            house_number = street_digits[0]
        else:
            house_number = False

        access_token = self._dimona_authenticate()

        data = {
            "employer": {
                "nssoRegistrationNumber": onss_registration_number,
            },
            "worker": {
                "ssin": niss if not foreigner else False,
                'lastName': last_name,
                'firstName': first_name,
                'birthDate': (self.employee_id.birthday or fields.Date.today()).strftime("%Y-%m-%d"),
                'birthPlace': self.employee_id.place_of_birth,
                'birthPlaceCountry': ONSS_COUNTRY_CODE_MAPPING.get(self.employee_id.country_of_birth.code),
                'nationality': ONSS_COUNTRY_CODE_MAPPING.get(self.employee_id.country_id.code),
                'gender': 'FEMALE' if self.employee_id.gender == 'female' else 'MALE',
                'address': {
                    'street': self.employee_id.private_street,
                    'houseNumber': house_number,
                    'zipCode': self.employee_id.private_zip,
                    'city': self.employee_id.private_city,
                    'country': ONSS_COUNTRY_CODE_MAPPING.get(self.employee_id.private_country_id.code)
                },
            },
            "dimonaIn": {
                "startingDate": self.date_start.strftime("%Y-%m-%d"),
                "dimonaFeatures": {
                    "jointCommissionNumber": "XXX",
                    "workerType": "OTH" if not self.l10n_be_is_student else "STU"
                }
            }
        }
        if self.date_end:
            data['dimonaIn']["endingDate"] = self.date_end.strftime("%Y-%m-%d")
        if self.l10n_be_dimona_planned_hours:
            data['dimonaIn']["plannedHoursNumber"] = self.l10n_be_dimona_planned_hours
        # Drop empty worker informations (The ONSS doesn't like it)
        data['worker']['address'] = {key: value for key, value in data['worker']['address'].items() if value}
        data['worker'] = {key: value for key, value in data['worker'].items() if value}

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % access_token,
        }
        try:
            response = requests.post(POST_ENDPOINT, json=data, headers=headers, timeout=DIMONA_TIMEOUT)
            if response.status_code == 201:
                result = response.headers
                self.l10n_be_dimona_in_declaration_number = result['Location'].split('/')[-1]
                self.l10n_be_dimona_last_declaration_number = self.l10n_be_dimona_in_declaration_number
                self.l10n_be_dimona_declaration_state = 'waiting'
                self.message_post(body=_('DIMONA IN declaration posted successfully, waiting validation'))
                self.env.ref('l10n_be_hr_payroll_dimona.ir_cron_check_dimona')._trigger(fields.Datetime.now() + timedelta(minutes=1))
            elif response.status_code == 400:
                raise UserError(_('Error with one or several invalid parameters on the POST request. Please contact an administrator. (%s)', response.text))
            elif response.status_code == 403:
                raise UserError(_('Your user does not have the rights to make a declaration for the employer. This happens, for example, if the user does not have or no longer has a mandate for the employer. (%s)', response.text))
            elif response.status_code == 500:
                raise UserError(_('Due to a technical problem at the ONSS side, the Dimona declaration could not be received by the ONSS.'))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))

    def _action_close_dimona(self):
        self.ensure_one()
        access_token = self._dimona_authenticate()

        data = {
            "dimonaOut": {
                "dimonaNumber": self.l10n_be_dimona_in_declaration_number,
                "endingDate": self.date_end.strftime("%Y-%m-%d"),
            }
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % access_token,
        }
        try:
            response = requests.post(POST_ENDPOINT, json=data, headers=headers, timeout=DIMONA_TIMEOUT)
            if response.status_code == 201:
                result = response.headers
                self.message_post(body=_('DIMONA Out declaration posted successfully, waiting validation'))
                self.l10n_be_dimona_last_declaration_number = result['Location'].split('/')[-1]
                self.l10n_be_dimona_declaration_state = 'waiting'
                self.env.ref('l10n_be_hr_payroll_dimona.ir_cron_check_dimona')._trigger(fields.Datetime.now() + timedelta(minutes=1))
            elif response.status_code == 400:
                raise UserError(_('Error with one or several invalid parameters on the POST request. Please contact an administrator. (%s)', response.text))
            elif response.status_code == 403:
                raise UserError(_('Your user does not have the rights to make a declaration for the employer. This happens, for example, if the user does not have or no longer has a mandate for the employer. (%s)', response.text))
            elif response.status_code == 500:
                raise UserError(_('Due to a technical problem at the ONSS side, the Dimona declaration could not be received by the ONSS.'))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))

    def _action_update_dimona(self):
        self.ensure_one()

        access_token = self._dimona_authenticate()

        data = {
            "dimonaUpdate": {
                "dimonaNumber": self.l10n_be_dimona_in_declaration_number,
                "startingDate": self.date_start.strftime("%Y-%m-%d")
            }
        }
        if self.date_end:
            data["dimonaUpdate"]["endingDate"] = self.date_end.strftime("%Y-%m-%d")
        if self.l10n_be_dimona_planned_hours:
            data['dimonaUpdate']["plannedHoursNumber"] = self.l10n_be_dimona_planned_hours

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % access_token,
        }
        try:
            response = requests.post(POST_ENDPOINT, json=data, headers=headers, timeout=DIMONA_TIMEOUT)
            if response.status_code == 201:
                result = response.headers
                self.message_post(body=_('DIMONA Update declaration posted successfully, waiting validation'))
                self.l10n_be_dimona_last_declaration_number = result['Location'].split('/')[-1]
                self.l10n_be_dimona_declaration_state = 'waiting'
                self.env.ref('l10n_be_hr_payroll_dimona.ir_cron_check_dimona')._trigger(fields.Datetime.now() + timedelta(minutes=1))
            elif response.status_code == 400:
                raise UserError(_('Error with one or several invalid parameters on the POST request. Please contact an administrator. (%s)', response.text))
            elif response.status_code == 403:
                raise UserError(_('Your user does not have the rights to make a declaration for the employer. This happens, for example, if the user does not have or no longer has a mandate for the employer. (%s)', response.text))
            elif response.status_code == 500:
                raise UserError(_('Due to a technical problem at the ONSS side, the Dimona declaration could not be received by the ONSS.'))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))

    def _action_cancel_dimona(self):
        self.ensure_one()
        access_token = self._dimona_authenticate()

        data = {
            "dimonaCancel": {
                "dimonaNumber": self.l10n_be_dimona_in_declaration_number,
            }
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % access_token,
        }
        try:
            response = requests.post(POST_ENDPOINT, json=data, headers=headers, timeout=DIMONA_TIMEOUT)
            if response.status_code == 201:
                result = response.headers
                self.message_post(body=_('DIMONA Cancel declaration posted successfully, waiting validation'))
                self.l10n_be_dimona_last_declaration_number = result['Location'].split('/')[-1]
                self.l10n_be_dimona_declaration_state = 'waiting'
                self.env.ref('l10n_be_hr_payroll_dimona.ir_cron_check_dimona')._trigger(fields.Datetime.now() + timedelta(minutes=1))
            elif response.status_code == 400:
                raise UserError(_('Error with one or several invalid parameters on the POST request. Please contact an administrator. (%s)', response.text))
            elif response.status_code == 403:
                raise UserError(_('Your user does not have the rights to make a declaration for the employer. This happens, for example, if the user does not have or no longer has a mandate for the employer. (%s)', response.text))
            elif response.status_code == 500:
                raise UserError(_('Due to a technical problem at the ONSS side, the Dimona declaration could not be received by the ONSS.'))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))

    def action_check_dimona(self):
        self.ensure_one()
        if not self.user_has_groups('hr_payroll.group_hr_payroll_user'):
            raise UserError(_("You don't have the right to call this action"))

        if not self.l10n_be_dimona_last_declaration_number:
            raise UserError(_("No DIMONA declaration is linked to this contract"))

        access_token = self._dimona_authenticate(declare=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % access_token,
        }
        try:
            response = requests.get(POST_ENDPOINT + '/' + url_quote(self.l10n_be_dimona_last_declaration_number), headers=headers, timeout=DIMONA_TIMEOUT)
            if response.status_code == 200:
                result = response.json()
                status = result['declarationStatus']['result']
                if status == 'A':
                    self.l10n_be_dimona_declaration_state = 'done'
                    self.message_post(body=_('DIMONA declaration treated and accepted without anomalies'))
                elif status == 'W':
                    self.l10n_be_dimona_declaration_state = 'done_warning'
                    self.message_post(body=_(
                        'DIMONA declaration treated and accepted with non blocking anomalies\n%s\n%s',
                        result['declarationStatus']['anomaliesCollection'],
                        result['declarationStatus']['informationsCollection']))
                elif status == 'B':
                    self.l10n_be_dimona_declaration_state = 'refused'
                    self.message_post(body=_(
                        'DIMONA declaration treated and refused (blocking anomalies)\n%s',
                        result['declarationStatus']['anomaliesCollection']))
                elif status == 'S':
                    self.l10n_be_dimona_declaration_state = 'waiting_sigedis'
                    self.message_post(body=_('DIMONA declaration waiting worker identification by Sigedis'))
            elif response.status_code == 400:
                raise UserError(_('Error with one or several invalid parameters on the POST request. Please contact an administrator. (%s)', response.text))
            elif response.status_code == 403:
                raise UserError(_('Your user does not have the rights to consult this declaration. This happens, for example, if the user does not have or no longer has a mandate for the employer. (%s)', response.text))
            elif response.status_code == 404:
                raise UserError(_('The declaration has been submitted but not processed yet or the declaration reference is not known. (%s)', response.text))
            elif response.status_code == 500:
                raise UserError(_('Due to a technical problem at the ONSS side, the Dimona declaration could not be received by the ONSS.'))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))

    @api.model
    def _cron_l10n_be_check_dimona(self, batch_size=50):
        contracts = self.search([
            ('l10n_be_dimona_declaration_state', '=', 'waiting'),
        ])
        if not contracts:
            return False
        contracts_batch = contracts[:batch_size]
        for contract in contracts_batch:
            try:
                # In case the ONSS is not available of if this is the declaration is not
                # processed yet fall silently to allow checking all the contracts of the batch
                contract.action_check_dimona()
            except Exception:
                contract.l10n_be_dimona_declaration_state = 'error'
        # if necessary, retrigger the cron to generate more pdfs
        if len(contracts) > batch_size:
            self.env.ref('l10n_be_hr_payroll_dimona.ir_cron_check_dimona')._trigger()
            return True
        return False
