# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, RedirectWarning

COUNTRY_CODE_MAP = {
    "BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU",
    "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA",
    "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA",
    "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM",
    "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF",
    "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB",
    "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND",
    "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ",
    "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM",
    "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB",
    "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG",
    "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL",
    "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT",
    "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN",
    "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM",
    "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU",
    "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK",
    "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW",
    "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR",
    "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK",
    "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE",
    "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA",
    "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN",
    "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR",
    "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT",
    "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM",
    "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND",
    "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"
}

class AccountMove(models.Model):
    _inherit = "account.move"

    # Extra selection after choosing l10n_id_kode_transaksi 07
    l10n_id_coretax_add_info_07 = fields.Selection([
        ('TD.00501', '1 - Pajak Pertambahan Nilai Tidak Dipungut berdasarkan PP Nomor 10 Tahun 2012'),
        ('TD.00502', '2 - Pajak Pertambahan Nilai atau Pajak Pertambahan Nilai dan Pajak Penjualan atas Barang Mewah tidak dipungut'),
        ('TD.00503', '3 - Pajak Pertambahan Nilai dan Pajak Penjualan atas Barang Mewah Tidak Dipungut'),
        ('TD.00504', '4 - Pajak Pertambahan Nilai Tidak Dipungut Sesuai PP Nomor 71 Tahun 2012'),
        ('TD.00505', '5 - (Tidak ada Cap)'),
        ('TD.00506', '6 - PPN dan/atau PPnBM tidak dipungut berdasarkan PMK No. 194/PMK.03/2012'),
        ('TD.00507', '7 - PPN Tidak Dipungut Berdasarkan PP Nomor 15 Tahun 2015'),
        ('TD.00508', '8 - PPN Tidak Dipungut Berdasarkan PP Nomor 69 Tahun 2015'),
        ('TD.00509', '9 - PPN Tidak Dipungut Berdasarkan PP Nomor 96 Tahun 2015'),
        ('TD.00510', '10 - PPN Tidak Dipungut Berdasarkan PP Nomor 106 Tahun 2015'),
        ('TD.00511', '11 - PPN Tidak Dipungut Sesuai PP Nomor 50 Tahun 2019'),
        ('TD.00512', '12 - PPN atau PPN dan PPnBM Tidak Dipungut Sesuai Dengan PP Nomor 27 Tahun 2017'),
        ('TD.00513', '13 - PPN ditanggung PEMERINTAH EX PMK 21/PMK.010/21'),
        ('TD.00514', '14 - PPN DITANGGUNG PEMERINTAH EKS PMK 102/PMK.010/2021'),
        ('TD.00515', '15 - PPN DITANGGUNG PEMERINTAH EKS PMK 239/PMK.03/2020'),
        ('TD.00516', '16 - Insentif PPN DITANGGUNG PEMERINTAH EKSEKUSI PMK NOMOR 103/PMK.010/2021'),
        ('TD.00517', '17 - PAJAK PERTAMBAHAN NILAI TIDAK DIPUNGUT BERDASARKAN PP NOMOR 40 TAHUN 2021'),
        ('TD.00518', '18 - PAJAK PERTAMBAHAN NILAI TIDAK DIPUNGUT BERDASARKAN PP NOMOR 41 TAHUN 2021'),
        ('TD.00519', '19 - PPN DITANGGUNG PEMERINTAH EKS PMK 6/PMK.010/2022'),
        ('TD.00520', '20 - PPN DITANGGUNG PEMERINTAH EKSEKUSI PMK NOMOR 226/PMK.03/2021'),
        ('TD.00521', '21 - PPN ATAU PPN DAN PPnBM TIDAK DIPUNGUT SESUAI DENGAN PP NOMOR 53 TAHUN 2017'),
        ('TD.00522', '22 - PPN tidak dipungut berdasarkan PP Nomor 70 Tahun 2021'),
        ('TD.00523', '23 - PPN ditanggung Pemerintah Ex PMK-125/PMK.01/2020'),
        ('TD.00524', '24 - (Tidak ada Cap)'),
        ('TD.00525', '25 - PPN tidak dipungut berdasarkan PP Nomor 49 Tahun 2022'),
        ('TD.00526', '26 - PPN tidak dipungut berdasarkan PP Nomor 12 Tahun 2023'),
        ('TD.00527', '27 - PPN ditanggung Pemerintah berdasarkan PMK Nomor 38 Tahun 2023')],
        compute="_compute_l10n_id_coretax_add_info",
        readonly=False,
        store=True
    )
    l10n_id_coretax_facility_info_07 = fields.Selection([
        ('TD.01101', '1 - untuk Kawasan Bebas'),
        ('TD.01102', '2 - untuk Tempat Penimbunan Berikat'),
        ('TD.01103', '3 - untuk Hibah dan Bantuan Luar Negeri'),
        ('TD.01104', '4 - untuk Avtur'),
        ('TD.01105', '5 - untuk Lainnya'),
        ('TD.01106', '6 - untuk Kontraktor Perjanjian Karya Pengusahaan Pertambangan Batubara Generasi I'),
        ('TD.01107', '7 - untuk Penyerahan bahan bakar minyak untuk Kapal Angkutan Laut Luar Negeri'),
        ('TD.01108', '8 - untuk Penyerahan jasa kena pajak terkait alat angkutan tertentu'), ('TD.01109', '9 - untuk Penyerahan BKP Tertentu di KEK'), ('TD.01110', '10 - untuk BKP tertentu yang bersifat strategis berupa anode slime'), ('TD.01111', '11 - untuk Penyerahan alat angkutan tertentu dan/atau Jasa Kena Pajak terkait alat angkutan tertentu'),
        ('TD.01112', '12 - untuk Penyerahan kepada Kontraktor Kerja Sama Migas yang mengikuti ketentuan Peraturan Pemerintah Nomor 27 Tahun 2017'),
        ('TD.01113', '13 - Penyerahan Rumah Tapak dan Satuan Rumah Susun Rumah Susun Ditanggung Pemerintah Tahun Anggaran 2021'),
        ('TD.01114', '14 - Penyerahan Jasa Sewa Ruangan atau Bangunan Kepada Pedagang Eceran yang Ditanggung Pemerintah Tahun Anggaran 2021'),
        ('TD.01115', '15 - Penyerahan Barang dan Jasa Dalam Rangka Penanganan Pandemi COVID-19 (PMK 239/PMK. 03/2020)'),
        ('TD.01116', '16 - Insentif PMK-103/PMK.010/2021 berupa PPN atas Penyerahan Rumah Tapak dan Unit Hunian Rumah Susun yang Ditanggung Pemerintah Tahun Anggaran 2021'),
        ('TD.01117', '17 - Kawasan Ekonomi Khusus PP nomor 40 Tahun 2021'),
        ('TD.01118', '18 - Kawasan Bebas PP nomor 41 Tahun 2021'),
        ('TD.01119', '19 - Penyerahan Rumah Tapak dan Unit Hunian Rumah Susun yang Ditanggung Pemerintah Tahun Anggaran 2022'),
        ('TD.01120', '20 - PPN Ditanggung Pemerintah dalam rangka Penanganan Pandemi Corona Virus'),
        ('TD.01121', '21 - Penyerahan kepada Kontraktor Kerja Sama Migas yang mengikuti ketentuan Peraturan Pemerintah Nomor 53 Tahun 2017'),
        ('TD.01122', '22 - BKP strategis tertentu dalam bentuk anode slime dan emas butiran'),
        ('TD.01123', '23 - untuk penyerahan kertas koran dan/atau majalah'),
        ('TD.01124', '24 - PPN tidak dipungut oleh Pemerintah lainnya'),
        ('TD.01125', '25 - BKP dan JKP tertentu'),
        ('TD.01126', '26 - Penyerahan BKP dan JKP di Ibu Kota Negara baru'),
        ('TD.01127', '27 - Penyerahan kendaraan listrik berbasis baterai')],
        compute="_compute_l10n_id_coretax_facility_info",
        readonly=False,
        store=True,
    )

    # Extra selection after choosing l10n_id_kode_transaksi 08
    l10n_id_coretax_add_info_08 = fields.Selection([
        ('TD.00501', '1 - PPN Dibebaskan Sesuai PP Nomor 146 Tahun 2000 Sebagaimana Telah Diubah Dengan PP Nomor 38 Tahun 2003'),
        ('TD.00502', '2 - PPN Dibebaskan Sesuai PP Nomor 12 Tahun 2001 Sebagaimana Telah Beberapa Kali Diubah Terakhir Dengan PP Nomor 31 Tahun 2007'),
        ('TD.00503', '3 - PPN dibebaskan berdasarkan Peraturan Pemerintah Nomor 28 Tahun 2009'),
        ('TD.00504', '4 - (Tidak ada cap)'),
        ('TD.00505', '5 - PPN Dibebaskan Sesuai Dengan PP Nomor 81 Tahun 2015'),
        ('TD.00506', '6 - PPN Dibebaskan Berdasarkan PP Nomor 74 Tahun 2015'),
        ('TD.00507', '7 - (tanpa cap)'),
        ('TD.00508', '8 - PPN DIBEBASKAN SESUAI PP NOMOR 81 TAHUN 2015 SEBAGAIMANA TELAH DIUBAH DENGAN PP 48 TAHUN 2020'),
        ('TD.00509', '9 - PPN DIBEBASKAN BERDASARKAN PP NOMOR 47 TAHUN 2020'),
        ('TD.00510', '10 - PPN Dibebaskan berdasarkan PP Nomor 49 Tahun 2022')],
        compute="_compute_l10n_id_coretax_add_info",
        readonly=False,
        store=True,
    )
    l10n_id_coretax_facility_info_08 = fields.Selection([
        ('TD.01101', '1 - PPN Dibebaskan Sesuai PP Nomor 146 Tahun 2000 Sebagaimana Telah Diubah Dengan PP Nomor 38 Tahun 2003'),
        ('TD.01102', '2 - PPN Dibebaskan Sesuai PP Nomor 12 Tahun 2001 Sebagaimana Telah Beberapa Kali Diubah Terakhir Dengan PP Nomor 31 Tahun 2007'),
        ('TD.01103', '3 - PPN dibebaskan berdasarkan Peraturan Pemerintah Nomor 28 Tahun 2009'),
        ('TD.01104', '4 - (Tidak ada cap)'),
        ('TD.01105', '5 - PPN Dibebaskan Sesuai Dengan PP Nomor 81 Tahun 2015'),
        ('TD.01106', '6 - PPN Dibebaskan Berdasarkan PP Nomor 74 Tahun 2015'),
        ('TD.01107', '7 - (tanpa cap)'),
        ('TD.01108', '8 - PPN DIBEBASKAN SESUAI PP NOMOR 81 TAHUN 2015 SEBAGAIMANA TELAH DIUBAH DENGAN PP 48 TAHUN 2020'),
        ('TD.01109', '9 - PPN DIBEBASKAN BERDASARKAN PP NOMOR 47 TAHUN 2020'),
        ('TD.01110', '10 - PPN Dibebaskan berdasarkan PP Nomor 49 Tahun 2022')],
        compute="_compute_l10n_id_coretax_facility_info",
        readonly=False,
        store=True,
    )

    l10n_id_kode_transaksi = fields.Selection(selection_add=[('10', '10 Other deliveries')])
    l10n_id_coretax_efaktur_available = fields.Boolean(compute="_compute_l10n_id_coretax_efaktur_available")
    l10n_id_coretax_document = fields.Many2one('l10n_id_efaktur_coretax.document', readonly=True, copy=False, string="e-Faktur Document")
    l10n_id_coretax_custom_doc = fields.Char(help="Additional documentation when choosing kode 07 or 08")

    def _compute_need_kode_transaksi(self):
        """ OVERRIDE: l10n_id_efaktur

        By setting this l10n_id_need_kode_transaksi, we can prevent the old E-Faktur flow to be
        triggered(i.e. efaktur range consumption).
        """
        self.l10n_id_need_kode_transaksi = False

    @api.depends('partner_id', 'line_ids.tax_ids')
    def _compute_l10n_id_coretax_efaktur_available(self):
        """ Similar use case as l10n_id_need_kode_transaksi from l10n_id_efaktur

        helps to check whether or not some fields need to be visible or not
        """
        for move in self:
            move.l10n_id_coretax_efaktur_available = (
                move.partner_id.l10n_id_pkp
                and move.country_code == 'ID'
                and move.move_type == 'out_invoice'
                and move.line_ids.tax_ids
            )

    # Interactions that is triggered when choosing kode 07 or 08
    # as they require additional information
    @api.depends("l10n_id_coretax_add_info_07", "l10n_id_coretax_add_info_08")
    def _compute_l10n_id_coretax_facility_info(self):
        for move in self:
            if move.l10n_id_kode_transaksi == "07":
                digits = move.l10n_id_coretax_add_info_07
                if digits:
                    move.l10n_id_coretax_facility_info_07 = f"TD.011{digits[-2:]}"
            elif move.l10n_id_kode_transaksi == "08":
                digits = move.l10n_id_coretax_add_info_08
                if digits:
                    move.l10n_id_coretax_facility_info_08 = f"TD.011{digits[-2:]}"

    @api.depends("l10n_id_coretax_facility_info_07", "l10n_id_coretax_facility_info_08")
    def _compute_l10n_id_coretax_add_info(self):
        for move in self:
            if move.l10n_id_kode_transaksi == "07":
                digits = move.l10n_id_coretax_facility_info_07
                if digits:
                    move.l10n_id_coretax_add_info_07 = f"TD.005{digits[-2:]}"
            elif move.l10n_id_kode_transaksi == "08":
                digits = move.l10n_id_coretax_facility_info_08
                if digits:
                    move.l10n_id_coretax_add_info_08 = f"TD.005{digits[-2:]}"

    def download_efaktur(self):
        """OVERRIDE l10n_id_efaktur

        Change the flow of efaktur downloading. Collects data needed for efaktur and generate the
        xml file.
        """
        # Pre-download checks

        # Should prevent users from generating e-Faktur document on invoices across multi-company.
        # Allowing it will cause issues on the invoice/eFaktur document record rule
        if len(self.company_id) > 1:
            raise UserError(_("You are not allowed to generate e-Faktur document from invoices coming from different companies"))

        err_messages = []

        if not self.company_id.vat:
            err_messages.append(_("Your company's VAT hasn't been configured yet"))

        # check for every customer
        for partner in self.partner_id:
            comm = partner.commercial_partner_id
            if not comm.l10n_id_pkp:
                err_messages.append(_("Customer %s is not taxable, tick ID PKP if necessary", comm.name))
            if comm.l10n_id_buyer_document_type != 'TIN' and not comm.l10n_id_buyer_document_number:
                err_messages.append(_("Document number for customer %s hasn't been filled in", comm.name))
            if not comm.vat:
                err_messages.append(_("NPWP for customer %s hasn't been filled in yet", comm.name))
            if not comm.country_id:
                err_messages.append(_("No country is set for customer %s", comm.name))

        # check for every invoice
        for record in self:
            if record.state == 'draft':
                err_messages.append(_('Invoice %s is in draft state', record.name))
            if not record.country_code == 'ID':
                err_messages.append(_("Invoice %s is not under Indonesian company", record.name))
            if not record.move_type == 'out_invoice':
                err_messages.append(_("Entry %s is not an invoice", record.name))
            if not record.line_ids.tax_ids:
                err_messages.append(_("Invoice %s does not contain any taxes", record.name))
            if record.l10n_id_kode_transaksi == "07":
                if not (record.l10n_id_coretax_add_info_07 and record.l10n_id_coretax_facility_info_07):
                    err_messages.append(_("Invoice %s doesn't contain the Additional info and Facility Stamp yet (Kode 07)", record.name))
            if record.l10n_id_kode_transaksi == "08":
                if not (record.l10n_id_coretax_add_info_08 and record.l10n_id_coretax_facility_info_08):
                    err_messages.append(_("Invoice %s doesn't contain the Additional info and Facility Stamp yet (Kode 08)", record.name))

        if err_messages:
            err_messages = [_('Unable to download E-faktur fot he following reasons(s):')] + err_messages
            raise ValidationError('\n - '.join(err_messages))

        # All invoices in self have no documents; we can create a new one for them.
        # Or all invoices in self have a document, but it's the same one. Special use case but we allow downloading it.
        if not self.l10n_id_coretax_document:
            self.l10n_id_coretax_document = self.env['l10n_id_efaktur_coretax.document'].create({
                'invoice_ids': self.ids,
                'company_id': self.company_id.id,
            })
            self.l10n_id_coretax_document._generate_xml()

        # If there is more than one document, or all invoices for a document were not selected, the resulting file could cause mistakes;
        # They could get a file with additional invoices for example. In this case, we redirect them to the document view to make it clearer.
        elif len(self.l10n_id_coretax_document) > 1 or set(self.l10n_id_coretax_document.invoice_ids.ids) != set(self.ids):
            action_error = {
                'name': _('Document Mismatch'),
                'view_mode': 'list',
                'res_model': 'l10n_id_efaktur_coretax.document',
                'type': 'ir.actions.act_window',
                'views': [[False, 'list'], [False, 'form']],
                'domain': [('id', 'in', self.l10n_id_coretax_document.ids)],
            }
            msg = _("The selected invoices are partially part of one or more e-faktur documents.\n"
                    "Please download them from the e-faktur documents directly.")
            raise RedirectWarning(msg, action_error, _("Display Related Documents"))

        return self.download_xml()

    def download_xml(self):
        return self.l10n_id_coretax_document.action_download()

    def _l10n_id_coretax_build_invoice_vals(self, vals):
        """ Fill in vals with invoice-related information """
        self.ensure_one()

        partner = self.commercial_partner_id
        trx_code = self.l10n_id_kode_transaksi

        vals.update({
            "TIN": self.company_id.vat,
            "TaxInvoiceDate": self.invoice_date.strftime("%Y-%m-%d"),
            "TaxInvoiceOpt": "Normal",
            "TrxCode": trx_code,
            "AddInfo": "",
            "CustomDoc": self.l10n_id_coretax_custom_doc or "",
            "CustomDocMonthYear": "",
            "FacilityStamp": "",
            "RefDesc": self.name,
            "SellerIDTKU": self.company_id.vat + self.company_id.partner_id.l10n_id_tku,
            "BuyerDocument": partner.l10n_id_buyer_document_type,
            "BuyerTin": partner.vat if partner.l10n_id_buyer_document_type == "TIN" else "0000000000000000",
            "BuyerCountry": COUNTRY_CODE_MAP.get(partner.country_id.code),
            "BuyerDocumentNumber": partner.l10n_id_buyer_document_number if partner.l10n_id_buyer_document_type != "TIN" else "",
            "BuyerName": self.partner_id.name,
            "BuyerAdress": self.partner_id.contact_address.replace('\n', ' ').strip(),
            "BuyerEmail": partner.email or "",
            "BuyerIDTKU": partner.vat + partner.l10n_id_tku,
        })

        if trx_code == '07':
            vals['AddInfo'] = self.l10n_id_coretax_add_info_07
            vals['FacilityStamp'] = self.l10n_id_coretax_facility_info_07
        elif trx_code == '08':
            vals['AddInfo'] = self.l10n_id_coretax_add_info_08
            vals['FacilityStamp'] = self.l10n_id_coretax_facility_info_08

    def prepare_efaktur_vals(self):
        """ Get information required from invoice and lines to generate E-Faktur that will be used
        to load in the XML template later on"""
        invoice_vals = []
        idr = self.env.ref('base.IDR')

        for move in self.filtered(lambda m: m.state == 'posted'):
            vals = {}
            move._l10n_id_coretax_build_invoice_vals(vals)

            for line in move.invoice_line_ids.filtered(lambda ml: ml.tax_ids):
                line._l10n_id_coretax_build_invoice_line_vals(vals)

            invoice_vals.append(vals)

        return invoice_vals
