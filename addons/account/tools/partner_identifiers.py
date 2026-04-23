from stdnum import (
    ean,
    lei,
)

from stdnum.ar import cuit as ar_cuit, dni as ar_dni
from stdnum.at import uid as at_en
from stdnum.au import acn as au_acn
from stdnum.be import vat as be_vat
from stdnum.br import cnpj as br_cnpj, cpf as br_cn
from stdnum.ch import uid as ch_uid
from stdnum.cl import rut as cl_rut
from stdnum.dk import cvr as dk_cvr
from stdnum.do import cedula as do_cedula, rnc as do_rnc
from stdnum.ec import ci as ec_ci, ruc as ec_ruc
from stdnum.ee import registrikood as ee_en
from stdnum.eu import vat as eu_vat
from stdnum.fi import ytunnus as fi_en
from stdnum.fr import nir as fr_cn, siret as fr_siret, siren as fr_siren
from stdnum.gt import nit as gt_nit
from stdnum.jp import cn as jp_en
from stdnum.lv import pvn as lv_en
from stdnum.ma import ice as ma_ice
from stdnum.no import orgnr as no_en
from stdnum.pe import cui as pe_cui, ruc as pe_ruc
from stdnum.se import orgnr as se_en
from stdnum.sg import uen as sg_en
from stdnum.uy import rut as uy_rut

from odoo.tools.translate import LazyTranslate
from odoo.addons.account.tools.partner_identifier_validation import (
    gt_cui_validate,
    nl_kvk_validate,
    nl_oin_validate,
    uy_ci_validate,
    uy_nie_validate,
    th_branch_code_validate
)
from odoo.addons.account.tools.country_groups import FR_AND_DOM_TOM, SEPA_COUNTRIES


_lt = LazyTranslate(__name__)

# -------------------------------------------------------------------------
# NAMING:
# - CN = citizen number (typically identification for individuals)
# - EN = enterprise number (typically what we used to have in company registry, local identification)
# - TIN = tax identification number (TIN, GST and VAT number are typically used to report taxes)
# - VAT = value added tax
# - GST = goods and services tax
# DOCUMENTATION:
# - https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
# -------------------------------------------------------------------------

GLN_SHARED_VALS = {
    'placeholder': '9780471117094',
    'validation_function': ean.validate,
}

SHADOWS_GLN = ['HR_EN', 'HU_EN', 'NZ_EN']

TIN_CATEGORIES = ['TIN', 'VAT', 'GST']
INDIVIDUAL_CATEGORIES = ['CN']  # citizen numbers — identify natural persons
COMPANY_CATEGORIES = [*TIN_CATEGORIES, 'EN']  # tax numbers (VAT/TIN/GST) and enterprise numbers — identify legal entities (companies)

IDENTIFIERS_METADATA = {
    'AD_VAT': {  # NRT
        # https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Andorra-TIN.pdf
        'scheme': '9922',
        'placeholder': 'U132950X',
        'category': 'VAT',
        'countries': ['AD'],
    },
    'AE_TIN': {
        'scheme': '0235',
        'category': 'TIN',
        'countries': ['AE'],
    },
    'AL_TIN': {  # NIPT
        'scheme': '9923',
        'placeholder': 'ALJ91402501L',
        'category': 'TIN',
        'countries': ['AL'],
    },
    'AR_AN': {
        'sequence': 11,
        'label': _lt('AN'),
        'help': _lt('Birth certificate / Acta de nacimiento.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CDI': {
        'sequence': 9,
        'label': _lt('CDI'),
        'help': _lt('Identification Code.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CDM': {
        'sequence': 13,
        'label': _lt('CdM'),
        'help': _lt('Migration Certificate / Certificado de migración.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CI': {
        'sequence': 6,
        'label': _lt('CI'),
        'help': _lt("Provincial ID card (Cédula de Identidad); the AFIP document type is derived from the partner's province."),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CIBAR': {
        'sequence': 12,
        'label': _lt('CIBAR'),
        'help': _lt('CI Bs. As. RNP.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CPF': {
        'sequence': 5,
        'label': _lt('CPF'),
        'help': _lt('CI Federal Police.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CUIL': {
        'sequence': 3,
        'label': _lt('CUIL'),
        'help': _lt('Unique Labor Identification Code (Código Único de Identificación Laboral).'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CUIT': {
        'sequence': 1,
        'label': _lt('CUIT'),
        'help': _lt('Unique Tax Identification Code (Código Único de Identificación Tributaria).'),
        'placeholder': '20055361682',
        'category': 'TIN',
        'validation_function': ar_cuit.validate,
        'countries': ['AR'],
    },
    'AR_DNI': {
        'sequence': 2,
        'label': _lt('DNI'),
        'help': _lt('National Identity Card (Documento Nacional de Identidad).'),
        'placeholder': '34586675',
        'category': 'CN',
        'validation_function': ar_dni.validate,
        'countries': ['AR'],
    },
    'AR_ET': {
        'sequence': 10,
        'label': _lt('ET'),
        'help': _lt('Pending (en trámite).'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_LC': {
        'sequence': 8,
        'label': _lt('LC'),
        'help': _lt('Libreta cívica.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_LE': {
        'sequence': 7,
        'label': _lt('LE'),
        'help': _lt('Libreta de enrolamiento.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_SIGD': {
        'sequence': 4,
        'label': _lt('SIGD'),
        'help': _lt('Unidentified / global daily sales (Sin identificar / venta global diaria).'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_UPAPP': {
        'sequence': 14,
        'label': _lt('UpApP'),
        'help': _lt('Used by Anses for Padrón.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AT_EN': {
        'sequence': 10,
        'scheme': '9915',
        'label': _lt('Company registry'),
        'help': _lt('Austrian company registry number (UID).'),
        'category': 'EN',
        'validation_function': at_en.validate,
        'countries': ['AT'],
    },
    'AT_VAT': {
        'scheme': '9914',
        'placeholder': 'ATU12345675',
        'category': 'VAT',
        'countries': ['AT'],
    },
    'AU_ACN': {
        'sequence': 10,
        'label': _lt('ACN'),
        'help': _lt('Australian Company Number.'),
        'placeholder': '004085616',
        'category': 'EN',
        'validation_function': au_acn.validate,
        'countries': ['AU'],
    },
    'AU_ABN': {
        'scheme': '0151',
        'placeholder': '83 914 571 673',
        'category': 'GST',
        'countries': ['AU'],
    },
    'BA_VAT': {
        'scheme': '9924',
        'category': 'VAT',
        'countries': ['BA'],
    },
    'BE_CN': {
        'sequence': 200,
        'scheme': '0008',
        'label': _lt('Citizen Identification'),
        'help': _lt('Belgian national identification number.'),
        'placeholder': '12.34.55-555.6',
        'countries': ['BE'],
    },
    'BE_EN': {
        'sequence': 10,
        'scheme': '0208',
        'label': _lt('BCE/KBO'),
        'help': _lt('Belgian Crossroads Bank for Enterprises number.'),
        'placeholder': '0477472701',
        'category': 'EN',
        'validation_function': be_vat.validate,
        'examples': ['0477472701', '1477472701'],
        'countries': ['BE'],
    },
    'BE_VAT': {
        'scheme': '9925',
        'placeholder': 'BE0477472701',
        'category': 'VAT',
        'countries': ['BE'],
    },
    'BG_VAT': {
        'scheme': '9926',
        'placeholder': 'BG1234567892',
        'category': 'VAT',
        'countries': ['BG'],
    },
    'BR_TIN': {  # CNPJ
        'label': _lt('CNPJ'),
        'placeholder': _lt('16.727.230/0001-97'),
        'help': _lt('Brazilian company identification number. 14 digits.'),
        'category': 'TIN',
        'validation_function': br_cnpj.validate,
        'countries': ['BR'],
    },
    'BR_CN': {  # CPF
        'sequence': 1,
        'label': _lt('CPF'),
        'placeholder': _lt('390.533.447-05'),
        'help': _lt('Brazilian individual identification number.'),
        'category': 'CN',
        'validation_function': br_cn.validate,
        'countries': ['BR'],
    },
    'CH_EN': {
        'sequence': 10,
        'scheme': '0183',
        'label': _lt('UIDB'),
        'help': _lt('Swiss company identification number (UIDB).'),
        'placeholder': 'CHE-100.155.212',
        'category': 'EN',
        'validation_function': ch_uid.validate,
        'countries': ['CH'],
    },
    'CH_VAT': {
        'scheme': '9927',
        'placeholder': _lt('CHE-123.456.788 TVA or CHE-123.456.788 MWST or CHE-123.456.788 IVA'),
        'category': 'VAT',
        'countries': ['CH'],
    },
    'CL_RUN': {
        'sequence': 2,
        'label': _lt('RUN'),
        'help': _lt('Registration.'),
        'placeholder': '12345678-5',
        'category': 'CN',
        'validation_function': cl_rut.validate,
        'countries': ['CL'],
    },
    'CL_RUT': {
        'sequence': 1,
        'label': _lt('RUT'),
        'help': _lt('RUT'),
        'placeholder': '76086428-5',
        'category': 'TIN',
        'validation_function': cl_rut.validate,
        'countries': ['CL'],
    },
    'CO_NIT': {
        'sequence': 1,
        'label': _lt('NIT'),
        'help': _lt('Número de Identificación Tributaria (Colombian company tax ID).'),
        'placeholder': '213123432-1',
        'category': 'TIN',
        'countries': ['CO'],
    },
    'CO_CC': {
        'sequence': 2,
        'label': _lt('Cédula de ciudadanía'),
        'help': _lt('Colombian citizenship ID card (Cédula de ciudadanía).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_RC': {
        'sequence': 3,
        'label': _lt('Registro Civil'),
        'help': _lt('Colombian civil registration document (Registro Civil).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_TI': {
        'sequence': 4,
        'label': _lt('Tarjeta de Identidad'),
        'help': _lt('Colombian identity card for minors (Tarjeta de Identidad).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_TE': {
        'sequence': 5,
        'label': _lt('Tarjeta de extranjería'),
        'help': _lt('Colombian foreigner card (Tarjeta de extranjería).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_CE': {
        'sequence': 6,
        'label': _lt('Cédula de extranjería'),
        'help': _lt('Colombian foreigner ID card (Cédula de extranjería).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_NIUP': {
        'sequence': 7,
        'label': _lt('NIUP'),
        'help': _lt('Número de Identificación Único Personal.'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_PEP': {
        'sequence': 8,
        'label': _lt('PEP'),
        'help': _lt('Permiso Especial de Permanencia.'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_PPT': {
        'sequence': 9,
        'label': _lt('PPT'),
        'help': _lt('Permiso por Protección Temporal.'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CR_CPJ': {
        'placeholder': '3101012009',
        'category': 'TIN',
        'countries': ['CR'],
    },
    'CY_VAT': {
        'scheme': '9928',
        'placeholder': 'CY10259033P',
        'category': 'VAT',
        'countries': ['CY'],
    },
    'CZ_VAT': {
        'scheme': '9929',
        'placeholder': 'CZ12345679',
        'category': 'VAT',
        'countries': ['CZ'],
    },
    'DE_GEBA': {
        'sequence': 10,
        'scheme': '0246',
        'label': _lt('GEBA'),
        'help': _lt('German Electronic Business Address.'),
        'placeholder': '',
        'countries': ['DE'],
    },
    'DE_LTW': {
        # EDI specific to invoice to government
        'sequence': 200,
        'scheme': '0204',
        'label': _lt('Leitweg-ID'),
        'help': _lt('Routing ID for invoicing German public authorities.'),
        'placeholder': '991-03730-19',
        # 'validation_function': de_leitweg.validate,  FIXME should upgrade stdnum to 2.1
        'countries': ['DE'],
    },
    'DE_VAT': {
        'scheme': '9930',
        'placeholder': _lt('DE123456788 or 12/345/67890'),
        'category': 'VAT',
        'countries': ['DE'],
    },
    'DK_CVR': {
        # All companies have a CVR number, prefixed or not with "DK".
        # Refers to the legal entity.
        'sequence': 10,
        'scheme': '0184',
        'label': _lt('CVR'),
        'help': _lt('Danish Central Business Register number.'),
        'placeholder': '58403288',
        'category': 'EN',
        'validation_function': dk_cvr.validate,
        'countries': ['DK'],
    },
    'DK_SE': {
        # A company might have multiple SE number for each department, prefixed or not with "DK".
        # Can be used in a VAT context if prefixed with "DK".
        # Refers to the tax entity.
        'sequence': 20,
        'scheme': '0198',
        'help': _lt('Danish tax entity number (SE-nummer).'),
        'label': _lt('SE'),
        'countries': ['DK'],
    },
    'DK_VAT': {
        # Same number as the CVR, but always prefixed.
        'placeholder': 'DK12345674',
        'category': 'VAT',
        'countries': ['DK'],
    },
    'DO_CEDULA': {
        'sequence': 2,
        'label': _lt('Cédula'),
        'help': _lt('Dominican Republic national identification number.'),
        'placeholder': '00113918205',
        'category': 'CN',
        'validation_function': do_cedula.validate,
        'countries': ['DO'],
    },
    'DO_RNC': {
        'sequence': 1,
        'label': _lt('RNC'),
        'help': _lt('Registro Nacional del Contribuyente.'),
        'placeholder': _lt('1-01-85004-3 or 101850043'),
        'category': 'TIN',
        'validation_function': do_rnc.validate,
        'countries': ['DO'],
    },
    'EC_DNI': {
        'sequence': 2,
        'label': _lt('Cédula'),
        'help': _lt('Citizenship card or Identity Card.'),
        'placeholder': '1714616123',
        'category': 'CN',
        'validation_function': ec_ci.validate,
        'countries': ['EC'],
    },
    'EC_RUC': {
        'sequence': 1,
        'label': _lt('RUC'),
        'help': _lt('Single Taxpayer Registration.'),
        'placeholder': _lt('1792060346001 or 1792060346'),
        'category': 'TIN',
        'validation_function': ec_ruc.validate,
        'countries': ['EC'],
    },
    'EE_EN': {
        'sequence': 10,
        'scheme': '0191',
        'label': _lt('Registrikood'),
        'help': _lt('Estonian business registry code.'),
        'placeholder': '12345678',
        'category': 'EN',
        'validation_function': ee_en.validate,
        'countries': ['EE'],
    },
    'EE_VAT': {  # KMKR
        'scheme': '9931',
        'placeholder': 'EE123456780',
        'category': 'VAT',
        'countries': ['EE'],
    },
    'ES_VAT': {  # NIF
        'scheme': '9920',
        'placeholder': 'ESA12345674',
        'category': 'VAT',
        'countries': ['ES'],
    },
    'FI_EN': {
        'sequence': 10,
        'scheme': '0216',
        'label': _lt('Business ID'),
        'help': _lt('Business ID (Y-tunnus).'),
        'placeholder': '8763054-9',
        'category': 'EN',
        'validation_function': fi_en.validate,
        'countries': ['FI', 'AX'],
    },
    'FI_VAT': {
        'scheme': '0213',
        'placeholder': 'FI12345671',
        'category': 'VAT',
        'countries': ['FI'],
    },
    'FR_CN': {
        'sequence': 200,
        'scheme': '0240',
        'label': _lt('France Register of legal persons'),
        'help': _lt('French national identification number (NIR).'),
        'placeholder': '295109912611193',
        'validation_function': fr_cn.validate,
        'countries': FR_AND_DOM_TOM,
    },
    'FR_CTC': {
        # EDI specific - French PDP/AP
        'sequence': 30,
        'scheme': '0225',
        'label': _lt('France FRCTC Electronic Address'),
        'help': _lt('Electronic address for French e-invoicing platforms (PDP/PPF).'),
        'countries': FR_AND_DOM_TOM,
    },
    'FR_SIREN': {
        'sequence': 20,
        'scheme': '0002',
        'label': _lt('SIREN'),
        'help': _lt('French 9-digit business identification number.'),
        'placeholder': '552008443',
        'category': 'EN',
        'validation_function': fr_siren.validate,
        'countries': FR_AND_DOM_TOM,
    },
    'FR_SIRET': {
        'sequence': 10,
        'scheme': '0009',
        'label': _lt('SIRET'),
        'help': _lt('French 14-digit establishment identification number (SIREN + NIC).'),
        'placeholder': '33417522101010',
        'category': 'EN',
        'validation_function': fr_siret.validate,
        'countries': FR_AND_DOM_TOM,
    },
    'FR_VAT': {
        'scheme': '9957',
        'placeholder': 'FR23334175221',
        'category': 'VAT',
        'countries': FR_AND_DOM_TOM,
    },
    'GB_VAT': {
        'scheme': '9932',
        'placeholder': _lt('GB123456782 or XI123456782'),
        'category': 'VAT',
        'countries': ['GB'],
    },
    'GR_VAT': {
        'scheme': '9933',
        'placeholder': 'EL123456783',
        'category': 'VAT',
        'countries': ['GR'],
    },
    'GT_CUI': {
        'sequence': 1,
        'label': _lt('CUI'),
        'help': _lt('Guatemalan unique identification code.'),
        'placeholder': '1234567890101',
        'category': 'CN',
        'validation_function': gt_cui_validate,
        'countries': ['GT'],
    },
    'GT_NIT': {
        'sequence': 2,
        'label': _lt('NIT'),
        'help': _lt('Número de Identificación Tributaria'),
        'placeholder': '576937K',
        'category': 'TIN',
        'validation_function': gt_nit.validate,
        'countries': ['GT'],
    },
    'HR_EN': {
        **GLN_SHARED_VALS,
        'sequence': 10,
        'label': _lt('Company Registry'),
        'help': _lt('Croatian company registry number.'),
        'category': 'EN',
        'countries': ['HR'],
    },
    'HR_VAT': {
        'scheme': '9934',
        'placeholder': 'HR01234567896',
        'category': 'VAT',
        'countries': ['HR'],
    },
    'HU_EN': {
        **GLN_SHARED_VALS,
        'sequence': 10,
        'label': _lt('Company Registry'),
        'help': _lt('Hungarian company registry number.'),
        'placeholder': _lt('12345678-1-11 or 8071592153'),
        'category': 'EN',
        'countries': ['HU'],
    },
    'HU_VAT': {  # That's the prefixed with HU VAT - the "EU" version
        'scheme': '9910',
        'placeholder': 'HU12345676',
        'category': 'VAT',
        'countries': ['HU'],
    },
    'ID_TIN': {
        'placeholder': '1234567890123456',
        'category': 'TIN',
        'countries': ['ID'],
    },
    'IE_VAT': {
        'scheme': '9935',
        'placeholder': 'IE1234567FA',
        'category': 'VAT',
        'countries': ['IE'],
    },
    'IL_VAT': {
        'placeholder': _lt('XXXXXXXXX [9 digits] and it should respect the Luhn algorithm checksum'),
        'category': 'VAT',
        'countries': ['IL'],
    },
    'IN_GST': {
        'placeholder': '12AAAAA1234AAZA',
        'category': 'GST',
        'countries': ['IN'],
    },
    'IS_VAT': {
        'scheme': '0196',
        'placeholder': 'IS062199',
        'category': 'VAT',
        'countries': ['IS'],
    },
    # Note: 'IT_CODICE' skipped for now, will need a refactor in itself.
    'IT_VAT': {
        'scheme': '0211',
        'label': _lt('IVA'),
        'placeholder': 'IT12345670017',
        'category': 'VAT',
        'countries': ['IT'],
    },
    'JP_EN': {
        'sequence': 10,
        'scheme': '0188',
        'label': _lt('SST'),
        'help': _lt('Japanese corporate number (Specified Subject to Tax).'),
        'placeholder': '7000012050002',
        'category': 'EN',
        'validation_function': jp_en.validate,
        'countries': ['JP'],
    },
    'JP_TIN': {
        'scheme': '0221',
        'label': _lt('IIN'),
        'placeholder': 'T7000012050002',
        'category': 'TIN',
        'countries': ['JP'],
    },
    'KR_TIN': {
        'placeholder': _lt('123-45-67890 or 1234567890'),
        'category': 'TIN',
        'countries': ['KR'],
    },
    'LEI': {
        'sequence': 100,
        'scheme': '0199',
        'label': _lt('LEI'),
        'help': _lt('Legal Entity Identifier'),
        'placeholder': '213800KUD8LAJWSQ9D15',
        'validation_function': lei.validate,
        'countries': SEPA_COUNTRIES,
    },
    'LI_VAT': {
        'scheme': '9936',
        'category': 'VAT',
        'countries': ['LI'],
    },
    'LT_JAK': {
        'sequence': 10,
        'scheme': '0200',
        'label': _lt('Company registry'),
        'help': _lt('Lithuanian legal entity code (JAK).'),
        'category': 'EN',
        'countries': ['LT'],
    },
    'LT_VAT': {
        'scheme': '9937',
        'placeholder': 'LT123456715',
        'category': 'VAT',
        'countries': ['LT'],
    },
    'LU_VAT': {
        'scheme': '9938',
        'placeholder': 'LU12345613',
        'category': 'VAT',
        'countries': ['LU'],
    },
    'LU_EN': {
        'label': _lt('Company registry'),
        'help': _lt('Luxembourg business registry number.'),
        'placeholder': '12345613',
        'category': 'EN',
        'countries': ['LU'],
    },
    'LV_EN': {
        'sequence': 10,
        'scheme': '0218',
        'label': _lt('Company registry'),
        'help': _lt('Latvian unified registration number.'),
        'placeholder': '40003521600',
        'category': 'EN',
        'validation_function': lv_en.validate,
        'countries': ['LV'],
    },
    'LV_VAT': {
        'scheme': '9939',
        'placeholder': 'LV41234567891',
        'category': 'VAT',
        'countries': ['LV'],
    },
    'MA_ICE': {
        'sequence': 10,
        'label': _lt('ICE'),
        'help': _lt('Moroccan joint business identifier (Identifiant Commun de l\'Entreprise).'),
        'placeholder': '001561191000066',
        'category': 'EN',
        'validation_function': ma_ice.validate,
        'countries': ['MA'],
    },
    'MA_TIN': {
        'placeholder': '12345678',
        'category': 'TIN',
        'countries': ['MA'],
    },
    'MC_VAT': {
        'scheme': '9940',
        'placeholder': 'FR53000004605',
        'category': 'VAT',
        'countries': ['MC'],
    },
    'ME_VAT': {
        'scheme': '9941',
        'placeholder': '02655284',
        'category': 'VAT',
        'countries': ['ME'],
    },
    'MK_VAT': {
        'scheme': '9942',
        'placeholder': 'MK4057009501106',
        'category': 'VAT',
        'countries': ['MK'],
    },
    'MT_VAT': {
        'scheme': '9943',
        'placeholder': 'MT12345634',
        'category': 'VAT',
        'countries': ['MT'],
    },
    'MX_RFC': {
        'placeholder': 'GODE561231GR8',
        'category': 'TIN',
        'countries': ['MX'],
    },
    'MY_EN': {
        'sequence': 10,
        'scheme': '0230',
        'label': _lt('Company registry'),
        'help': _lt('Malaysian company registration number.'),
        'category': 'EN',
        'countries': ['MY'],
    },
    'NG_VAT': {
        'scheme': '0244',
        'category': 'VAT',
        'countries': ['NG'],
    },
    'NL_KVK': {
        'sequence': 10,
        'scheme': '0106',
        'help': _lt('Dutch Chamber of Commerce registration number.'),
        'label': _lt('KVK'),
        'placeholder': '12345678',
        'category': 'EN',
        'validation_function': nl_kvk_validate,
        'countries': ['NL'],
    },
    'NL_OIN': {
        'sequence': 20,
        'scheme': '0190',
        'help': _lt('Dutch government Organisation Identification Number.'),
        'label': _lt('OIN'),
        'placeholder': '00000003123456780000',
        'category': 'EN',
        'validation_function': nl_oin_validate,
        'countries': ['NL'],
    },
    'NL_VAT': {
        'scheme': '9944',
        'placeholder': 'NL123456782B90',
        'category': 'VAT',
        'countries': ['NL'],
    },
    'NO_EN': {
        'sequence': 10,
        'scheme': '0192',
        'label': _lt('Brønnøysund nr'),
        'help': _lt('Norwegian Register of Legal Entities (Brønnøysund Register Center)'),
        'placeholder': '974 760 673',
        'category': 'EN',
        'validation_function': no_en.validate,
        'countries': ['NO'],
    },
    'NO_VAT': {
        'placeholder': 'NO123456785',
        'category': 'VAT',
        'countries': ['NO'],
    },
    'NZ_EN': {
        **GLN_SHARED_VALS,
        'sequence': 10,
        'label': _lt('NZBN'),
        'help': _lt('New Zealand Business Number.'),
        'category': 'EN',
        'countries': ['NZ'],
    },
    'NZ_GST': {
        'placeholder': _lt('49-098-576 or 49098576'),
        'category': 'GST',
        'countries': ['NZ'],
    },
    'PE_CPP': {
        'sequence': 12,
        'label': _lt('License Permit Temp. Perman.'),
        'help': _lt('Carné Permiso Temp. Perman.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_CUI': {  # CUI <-> RUT : to_ruc/to_dni
        'sequence': 1,
        'label': _lt('Company registry'),
        'help': _lt('Peruvian unique taxpayer registry number (RUC).'),
        'placeholder': '101174102',
        'category': 'EN',
        'countries': ['PE'],
    },
    'PE_DIC': {
        'sequence': 5,
        'label': _lt('Diplomatic Identity Card'),
        'help': _lt('Cédula Diplomática de identidad.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_DNI': {
        'sequence': 3,
        'label': _lt('DNI'),
        'help': _lt('National Identity Document.'),
        'placeholder': '40000004',
        'category': 'CN',
        'validation_function': pe_cui.validate,
        'countries': ['PE'],
    },
    'PE_IDCR': {
        'sequence': 6,
        'label': _lt('Identity document of the country of residence'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_IN': {
        'sequence': 8,
        'label': _lt('Identification Number'),
        'help': _lt('IN - Doc Trib PP. JJ.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_NDTD': {
        'sequence': 4,
        'label': _lt('Non-Domiciled Tax Document'),
        'help': _lt('Document without RUC from another country.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_PTP': {
        'sequence': 10,
        'label': _lt('PTP'),
        'help': _lt('Temporary Residence Permit (Permiso de residencia temporal).'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_RUC': {
        'sequence': 2,
        'label': _lt('RUC'),
        'help': _lt('Taxpayer Identification Number.'),
        'placeholder': _lt('10XXXXXXXXY or 20XXXXXXXXY or 15XXXXXXXXY or 16XXXXXXXXY or 17XXXXXXXXY'),
        'category': 'TIN',
        'validation_function': pe_ruc.validate,
        'countries': ['PE'],
    },
    'PE_SP': {
        'sequence': 11,
        'label': _lt('Safe Passage'),
        'help': _lt('Salvoconducto.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_TAM': {
        'sequence': 9,
        'label': _lt('TAM'),
        'help': _lt('Andean Immigration Card.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_TIN': {
        'sequence': 7,
        'label': _lt('Tax Identification Number'),
        'help': _lt('TIN – Doc Trib PP.NN.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PH_TIN': {
        'placeholder': '123-456-789-123',
        'category': 'TIN',
        'countries': ['PH'],
    },
    'PL_VAT': {  # NIP
        'scheme': '9945',
        'placeholder': 'PL1234567883',
        'category': 'VAT',
        'countries': ['PL'],
    },
    'PT_VAT': {  # NIF
        'scheme': '9946',
        'placeholder': 'PT123456789',
        'category': 'VAT',
        'countries': ['PT'],
    },
    'RO_VAT': {
        'scheme': '9947',
        'placeholder': _lt('RO1234567897 or 8001011234567 or 9000123456789'),
        'category': 'VAT',
        'countries': ['RO'],
    },
    'RS_VAT': {
        'scheme': '9948',
        'placeholder': 'RS101134702',
        'category': 'VAT',
        'countries': ['RS'],
    },
    'RU_TIN': {
        'placeholder': '123456789047',
        'category': 'TIN',
        'countries': ['RU'],
    },
    'SA_GST': {
        'placeholder': _lt('310175397400003 [Fifteen digits, first and last digits should be "3"]'),
        'category': 'GST',
        'countries': ['SA'],
    },
    'SE_EN': {
        'sequence': 10,
        'scheme': '0007',
        'label': _lt('Company registry'),
        'help': _lt('Swedish organization number (Organisationsnummer).'),
        'placeholder': '1234567897',
        'category': 'EN',
        'validation_function': se_en.validate,
        'countries': ['SE'],
    },
    'SE_VAT': {
        'scheme': '9955',
        'placeholder': 'SE123456789701',
        'category': 'VAT',
        'countries': ['SE'],
    },
    'SG_UEN': {
        'sequence': 10,
        'scheme': '0195',
        'label': _lt('UEN'),
        'help': _lt('Singapore Unique Entity Number.'),
        'placeholder': '00192200M',
        'category': 'EN',
        'validation_function': sg_en.validate,
        'countries': ['SG'],
    },
    'SG_GST': {
        # Note: For most companies registered after 2009, the GST Registration Number is identical to their UEN.
        'sequence': 10,
        'placeholder': '00192200M',
        'category': 'GST',
        'countries': ['SG'],
    },
    'SI_VAT': {
        'scheme': '9949',
        'placeholder': 'SI12345679',
        'category': 'VAT',
        'countries': ['SI'],
    },
    'SK_EN': {
        'sequence': 10,
        'scheme': '0245',
        'label': _lt('Company registry'),
        'help': _lt('Slovak company identification number (IČO).'),
        'category': 'EN',
        'countries': ['SK'],
    },
    'SK_VAT': {
        'scheme': '9950',
        'placeholder': 'SK2022749619',
        'category': 'VAT',
        'countries': ['SK'],
    },
    'SM_VAT': {
        'scheme': '9951',
        'placeholder': 'SM24165',
        'category': 'VAT',
        'countries': ['SM'],
    },
    'TH_VAT': {
        'placeholder': '1234545678781',
        'category': 'VAT',
        'countries': ['TH'],
    },
    'TH_BRANCH_CODE': {
        'sequence': 20,
        'label': _lt('Branch Code'),
        'help': _lt('The 5-digit branch code as registered with the Revenue Department. Leave empty for Head Office.'),
        'placeholder': '00000',
        'category': 'EN',
        'validation_function': th_branch_code_validate,
        'countries': ['TH'],
    },
    'TR_VAT': {
        'scheme': '9952',
        'placeholder': _lt('11111111111 (NIN) or 2222222222 (VKN)'),
        'category': 'VAT',
        'countries': ['TR'],
    },
    'UA_TIN': {  # stdnum.ua.rntrc
        'placeholder': _lt("12345678 or UA12345678 (EDRPOU), 1234567890 (RNOPP) or 123456789012 (IPN)"),
        'category': 'TIN',
        'countries': ['UA'],
    },
    'US_TIN': {
        'scheme': '9959',
        'placeholder': '123-45-6789',
        'category': 'TIN',
        'countries': ['US'],
    },
    'UY_CI': {
        'sequence': 3,
        'label': _lt('CI'),
        'help': _lt('Cédula de Identidad (Uruguayan ID card).'),
        'placeholder': '3:402.010-1',
        'category': 'CN',
        'validation_function': uy_ci_validate,
        'countries': ['UY'],
    },
    'UY_DNI': {
        'sequence': 5,
        'label': _lt('DNI'),
        'help': _lt('Documento Nacional de Identidad (AR, BR, CL or PY).'),
        'category': 'CN',
        'countries': ['UY'],
    },
    'UY_NIE': {
        'sequence': 1,
        'label': _lt('NIE'),
        'help': _lt('Foreigner Identity Number.'),
        'placeholder': '93:402.010-1',
        'category': 'CN',
        'validation_function': uy_nie_validate,
        'countries': ['UY'],
    },
    'UY_NIFE': {
        'sequence': 6,
        'label': _lt('NIFE'),
        'help': _lt('Foreign tax identification number.'),
        'category': 'CN',
        'countries': ['UY'],
    },
    'UY_OTR': {
        'sequence': 4,
        'label': _lt('Otros'),
        'help': _lt('Other identification document.'),
        'category': 'CN',
        'countries': ['UY'],
    },
    'UY_RUT': {
        'sequence': 2,
        'label': _lt('RUT'),
        'help': _lt('Registro Único Tributario / Registro Único de Contribuyente.'),
        'placeholder': _lt("211003420017"),
        'category': 'TIN',
        'validation_function': uy_rut.validate,
        'countries': ['UY'],
    },
    'VA_VAT': {
        'scheme': '9953',
        'category': 'VAT',
        'countries': ['VA'],
    },
    'VE_RIF': {
        'placeholder': 'V-12345678-1, V123456781, V-12.345.678-1',
        'category': 'TIN',
        'countries': ['VE'],
    },
    'XI_TIN': {
        'placeholder': 'XI123456782',
        'category': 'TIN',
        'countries': ['XI'],
    },
    # Keep international identifiers at the end of the dict
    'DUNS': {
        'sequence': 100,
        'scheme': '0060',
        'label': _lt('DUNS'),
        'help': _lt('Dun & Bradstreet unique 9-digit business identifier.'),
        'placeholder': '372441183',
        'countries': False,
    },
    'PASSPORT': {
        'sequence': 95,
        'label': _lt('Passport'),
        'help': _lt('Passport number.'),
        'category': 'CN',
        'countries': ['AR', 'PE', 'CO', 'UY', 'EC'],
    },
    'EAN_GLN': {
        **GLN_SHARED_VALS,
        'sequence': 200,
        'scheme': '0088',
        'label': _lt('EAN/GLN'),
        'help': _lt('Global Location Number, used to identify parties and locations.'),
        'countries': False,
    },
    'GS1': {
        'sequence': 200,
        'scheme': '0209',
        'label': _lt('GS1 identification keys'),
        'help': _lt('GS1 identification keys for supply chain management.'),
        'countries': False,
    },
    'IBAN': {
        # EDI specific don't mix up with account_number
        'sequence': 200,
        'scheme': '9918',
        'label': _lt('IBAN'),
        'help': _lt('International Bank Account Number, used as an EDI identifier.'),
        'countries': False,
    },
}

TIN_METADATA = {
    key: metadata for key, metadata
    in IDENTIFIERS_METADATA.items()
    if metadata.get('category') in TIN_CATEGORIES
}

ADDITIONAL_IDENTIFIERS_METADATA = {
    key: metadata for key, metadata
    in IDENTIFIERS_METADATA.items()
    if metadata.get('category') not in TIN_CATEGORIES
}

ISO_IDENTIFIERS_METADATA = {
    metadata.get('scheme'): {'key': key, **metadata}
    for key, metadata in IDENTIFIERS_METADATA.items()
    if metadata.get('scheme')
}


def is_tin(identifier_type):
    """ Whether the identifier is a Tax Identification Number (VAT/GST, ...). """
    return identifier_type in TIN_METADATA


def is_individual_identifier(identifier_type):
    """ Whether the identifier represents an individual (e.g. a citizen number). """
    return get_identifier_metadata(identifier_type).get('category') in INDIVIDUAL_CATEGORIES


def is_company_identifier(identifier_type):
    """ Whether the identifier represents a company (a tax number or an enterprise number). """
    return get_identifier_metadata(identifier_type).get('category') in COMPANY_CATEGORIES


def get_identifier_metadata(identifier_type):
    """Metadata dict for `identifier_type`."""
    return IDENTIFIERS_METADATA.get(identifier_type) or {}


def pick_preferred_identifier(identifiers, filter_func=None, sort_key=None):
    """ Pick the best identifier from a candidates dict.

    :param identifiers: dict {identifier_type: value} as from `_get_all_identifiers()`
    :param filter_func: optional (key, value, metadata) -> bool
    :param sort_key: optional (key, value, metadata) -> comparable
    :return: dict `{'key': ..., 'value': ..., **metadata}` of the winner, or empty dict if no candidate.
    """
    candidates = []
    for key, value in identifiers.items():
        meta = get_identifier_metadata(key)
        if filter_func and not filter_func(key, value, meta):
            continue
        candidates.append((key, value, meta))
    if not candidates:
        return {}
    if sort_key:
        candidates.sort(key=lambda c: sort_key(*c))
    winner_key, winner_value, winner_meta = candidates[0]
    return {'key': winner_key, 'value': winner_value, **winner_meta}


def get_tin_metadata_of_country(country_code):
    """ First TIN metadata mapped to `country_code`; we assume one tax ID per country. """
    for key, metadata in TIN_METADATA.items():
        if country_code in (TIN_METADATA[key].get('countries') or []):
            return {'key': key, **metadata}
    return {}


def get_tin_label_of_country(country_code):
    """ Label for the country's tax ID. """
    return get_tin_metadata_of_country(country_code).get('label')


def get_tin_placeholder_of_country(country_code):
    """ Example value for the country's tax ID, used as placeholder. """
    return get_tin_metadata_of_country(country_code).get('placeholder')


def get_additional_identifiers_metadata_of_country(country_code, include_international=True, seq_min=0, seq_max=100):
    """ Identifiers that should be offered for `country_code`, optionally narrowed by the
    `sequence`.
    """
    result = {}
    for key, metadata in ADDITIONAL_IDENTIFIERS_METADATA.items():
        if not seq_min <= metadata.get('sequence', 100) <= seq_max:
            continue
        if country_code not in (metadata.get('countries') or []) and not (
            include_international and not metadata.get('countries')
        ):
            continue
        result[key] = metadata
    return result


def get_identifier_label(identifier_type):
    """ Label for the identifier. """
    return get_identifier_metadata(identifier_type).get('label')


def get_deduced_identifiers(key, value):
    """ Identifiers derivable from `(key, value)` identifier.
    Example: FR_SIRET => FR_SIREN, BE_VAT => BE_EN.
    """
    deduced = {}
    if key == 'AT_VAT':
        deduced['AT_EN'] = get_non_prefixed_identifier('AT', value)
    if key == 'AU_ACN':
        deduced['AU_ANB'] = au_acn.to_abn(value)
    if key == 'BE_VAT':
        deduced['BE_EN'] = get_non_prefixed_identifier('BE', value)
    if key == 'DK_VAT':
        deduced['DK_CVR'] = get_non_prefixed_identifier('DK', value)
    if key == 'FR_SIRET':
        deduced['FR_SIREN'] = fr_siret.to_siren(value)
    if key == 'SG_GST':
        deduced['SG_UEN'] = value
    if key == 'LU_VAT':
        deduced['LU_EN'] = get_non_prefixed_identifier('LU', value)
    return deduced


def get_prefixed_identifier(country_code, value):
    """ Add the country prefix.
    Example: "0477472701" => "BE0477472701".
    """
    if value.startswith(country_code):
        return value  # keep idempotent
    if country_code == 'HU':
        return f'{country_code}{value[:8]}'
    return f'{country_code}{value}'


def get_non_prefixed_identifier(country_code, value):
    """ Strip the country prefix from identifier. """
    if not value.startswith(country_code):
        return value  # keep idempotent
    return value.removeprefix(country_code)


def is_identifier_void(identifier):
    """ True for the user-entered placeholders that mean "no value" (e.g. "/", "N/A");"""
    if not identifier:
        return True
    return identifier in ('/', 'na', 'NA', 'N/A', 'not applicable')


def normalize_identifier(identifier_type, value):
    """ Very basic normalization of identifier, handle the "no value" placeholders. """
    value = value if not is_identifier_void(value) else None
    if not value:
        return value
    return value.strip()


def validate_identifier(identifier_type, value):
    """ Run the per-scheme stdnum validator (if any) and return a uniform
    `{valid, value, example}` dict.
    """
    value = normalize_identifier(identifier_type, value)
    if not value:
        return {'valid': True, 'value': value, 'example': None}

    metadata = get_identifier_metadata(identifier_type)
    example = metadata.get('examples') or metadata.get('placeholder')
    function_validation = metadata.get('validation_function')
    if not function_validation and metadata.get('category') == 'VAT':
        function_validation = eu_vat.validate
    if function_validation:
        try:
            value_normalized = function_validation(value)
        except Exception:  # noqa: BLE001
            return {'valid': False, 'value': value, 'example': example}
        else:
            return {'valid': True, 'value': value_normalized, 'example': example}
    return {'valid': True, 'value': value, 'example': example}


def format_participant_identifier(identifier_type, value):
    """ Format the identifier such as `eas_scheme:identifier`.
    This format is used in many EDIs.
    """
    if eas := get_identifier_metadata(identifier_type).get('scheme'):
        return f'{eas}:{value}'
    return None


def validate_participant_identifier(identifier):
    """ Validate and normalize identifier formated `eas_scheme:identifier`. """
    assert ':' in identifier
    iso_scheme, _sep, value = identifier.partition(':')
    identifier = ISO_IDENTIFIERS_METADATA[iso_scheme]
    validation = validate_identifier(identifier['key'], value)
    validation['value'] = f'{iso_scheme}:{validation['value']}'
    return validation


def validation_error_message(env, identifier_type, example=None):
    """ Return error message to use everywhere a malformed identifier
    is rejected.
    """
    example = env._("\nExample: %(example)s", example=example) if example else ""
    return env._(
        "Invalid identifier: %(identifier)s.%(example)s",
        identifier=get_identifier_label(identifier_type),
        example=example
    )
