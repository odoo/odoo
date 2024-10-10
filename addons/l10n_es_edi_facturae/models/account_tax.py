import csv

from odoo import api, fields, models
from odoo.tools import file_open


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_es_edi_facturae_tax_type = fields.Selection((
        ('01', 'Value-Added Tax'),
        ('02', 'Taxes on production, services and imports in Ceuta and Melilla'),
        ('03', 'IGIC: Canaries General Indirect Tax'),
        ('04', 'IRPF: Personal Income Tax'),
        ('05', 'Other'),
        ('06', 'ITPAJD: Tax on wealth transfers and stamp duty'),
        ('07', 'IE: Excise duties and consumption taxes'),
        ('08', 'RA: Customs duties'),
        ('09', 'IGTECM: Sales tax in Ceuta and Melilla'),
        ('10', 'IECDPCAC: Excise duties on oil derivates in Canaries'),
        ('11', 'IIIMAB: Tax on premises that affect the environment in the Balearic Islands'),
        ('12', 'ICIO: Tax on construction, installation and works'),
        ('13', 'IMVDN: Local tax on unoccupied homes in Navarre'),
        ('14', 'IMSN: Local tax on building plots in Navarre'),
        ('15', 'IMGSN: Local sumptuary tax in Navarre'),
        ('16', 'IMPN: Local tax on advertising in Navarre'),
        ('17', 'REIVA: Special VAT for travel agencies'),
        ('18', 'REIGIC: Special IGIC: for travel agencies'),
        ('19', 'REIPSI: Special IPSI for travel agencies'),
        ('20', 'IPS: Insurance premiums Tax'),
        ('21', 'SWUA: Surcharge for Winding Up Activity'),
        ('22', 'IVPEE: Tax on the value of electricity generation'),
        ('23', 'Tax on the production of spent nuclear fuel and radioactive waste from the generation of nuclear electric power'),
        ('24', 'Tax on the storage of spent nuclear energy and radioactive waste in centralised facilities'),
        ('25', 'IDEC: Tax on bank deposits'),
        ('26', 'Excise duty applied to manufactured tobacco in Canaries'),
        ('27', 'IGFEI: Tax on Fluorinated Greenhouse Gases'),
        ('28', 'IRNR: Non-resident Income Tax'),
        ('29', 'Corporation Tax'),
    ), string='Spanish Facturae EDI Tax Type', default='01')

    @api.model
    def _update_l10n_es_edi_facturae_tax_type(self):
        """
            Applies all existing tax l10n_es_edi_facturae_tax_type field to their proper value if any link between tax and their template is found
        """
        concerned_company_ids = [
            company.id
            for company in self.env.companies
            if company.chart_template and company.chart_template.startswith('es_')
        ]
        if not concerned_company_ids:
            return
        current_taxes = self.env['account.tax'].search(self.env['account.tax']._check_company_domain(concerned_company_ids))
        if not current_taxes:
            return
        with file_open('l10n_es_edi_facturae/data/template/account.tax-es_common.csv') as template_file:
            template_data = {record['id']: record['l10n_es_edi_facturae_tax_type'] for record in csv.DictReader(template_file)}
        xmlid2tax = {
            xml_id.split('.')[1].split('_', maxsplit=1)[1]: self.env['account.tax'].browse(record)
            for record, xml_id in current_taxes.get_external_id().items() if xml_id.startswith('account.')
        }
        for xmlid, facturae_tax_type in template_data.items():
            # Only update the tax_type fields
            xmlid = xmlid.split('.')[1]
            oldtax = xmlid2tax.get(xmlid)
            if oldtax and oldtax.l10n_es_edi_facturae_tax_type != facturae_tax_type:
                oldtax.l10n_es_edi_facturae_tax_type = facturae_tax_type
