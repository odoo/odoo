# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Shared-core codes also valid for VeriFactu, sale side only (excludes '11'/'12_sale'/'13_sale':
# VeriFactu uses its own '11_vf' instead).
VERIFACTU_SHARED_CODES = [
    '01', '02_sale', '03', '04', '05', '07', '08', '09_sale', '10', '14_sale', '15',
]

# L8A: ClaveRegimen values valid when the tax applicability is IVA (or IPSI/"Other", which fall
# back to this list — the AEAT spec doesn't define a distinct list for those, see l10n_es_applicability).
VERIFACTU_REGIME_CODES_IVA = VERIFACTU_SHARED_CODES + ['11_vf', '17', '18_iva', '19_iva', '20']

# L8B: ClaveRegimen values valid when the tax applicability is IGIC. No '20' equivalent exists.
VERIFACTU_REGIME_CODES_IGIC = VERIFACTU_SHARED_CODES + ['11_vf', '17_igic_sale', '18_igic_sale', '19_igic_sale']

# ir.config_parameter key holding a random value generated when the module is installed and removed
# when it is uninstalled. It is combined with database.uuid to compute the SistemaInformatico
# NumeroInstalacion, so that each installation of the module (e.g. after a reinstall) gets a new one.
VERIFACTU_INSTALLATION_SALT_PARAM = 'l10n_es_edi_verifactu.installation_salt'
