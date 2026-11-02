# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Thai Tax Reports",
    "version": "19.0.1.15.0",
    "category": "Localization",
    "summary": "Thai tax reports: VAT Sales/Purchase Register, "
    "PP30 Register (แบบแสดงรายการภาษีมูลค่าเพิ่ม ภ.พ.30), "
    "WHT Register, "
    "WHT Certificate (หนังสือรับรองการหักภาษี ณ ที่จ่าย), "
    "PND3 Register (ภ.ง.ด.3 บุคคลธรรมดา), "
    "PND53 Register (ภ.ง.ด.53 นิติบุคคล), PND54 Register, "
    "PP40 SBT Register (ภาษีธุรกิจเฉพาะ ภ.ธ.40), "
    "PND50/PND51 Register (ภาษีเงินได้นิติบุคคล), "
    "Deferred Tax Worksheet (TAS 12 ภาษีเงินได้รอตัดบัญชี), "
    "NPAE Financial Statement (งบการเงินตามแบบ NPAE), "
    "SBC3 DBD Filing (งบการเงินนำส่ง DBD ส.บช.3), "
    "Stamp Duty Register (ทะเบียนอากรแสตมป์), "
    "e-Withholding Tax submission",
    "author": "Custom",
    "website": "https://github.com/OCA/l10n-thailand",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
        "l10n_th_account_tax",
        "od19_partner_thai_fields",
        "od19_accounting_dncn",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/od19_vat_non_deductible_data.xml",
        "data/od19_reverse_charge_data.xml",
        "data/od19_sbt_data.xml",
        "data/od19_stamp_duty_data.xml",
        "wizard/tax_report_wizard_views.xml",
        "report/vat_sales_register.xml",
        "report/vat_purchase_register.xml",
        "report/wht_register.xml",
        "report/wht_certificate.xml",
        "report/pp30_register.xml",
        "report/pp36_register.xml",
        "report/pnd3_register.xml",
        "report/pnd53_register.xml",
        "report/pnd54_register.xml",
        "report/pnd50_register.xml",
        "report/pnd51_register.xml",
        "report/npae_financial_statement.xml",
        "report/sbc3_register.xml",
        "report/sbt_pp40_register.xml",
        "report/stamp_duty_register.xml",
        "report/tax_invoice_forms.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "views/ewht_submission_views.xml",
        "views/deferred_tax_views.xml",
        "views/od19_stamp_duty_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_thai_tax_reports/static/description/icon.svg",
}
