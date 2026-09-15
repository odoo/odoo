from typing import Literal

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.l10n_ro_edi_stock.models.l10n_ro_edi_stock_document import (
    DOCUMENT_STATES,
)

OPERATION_TYPES = [
    ("10", "Intra-community purchase"),
    ("12", "Operations in lohn system (EU) - input"),
    ("14", "Stocks available to the customer (Call-off stock) - entry"),
    ("20", "Intra-Community delivery"),
    ("22", "Operations in lohn system (EU) - exit"),
    ("24", "Stocks available to the customer (Call-off stock) - exit"),
    ("30", "Transport on the national territory"),
    ("40", "Import"),
    ("50", "Export"),
    (
        "60",
        "Intra-community transaction - Entry for storage/formation of new transport",
    ),
    (
        "70",
        "Intra-community transaction - Exit after storage/formation of new transport",
    ),
]

OPERATION_SCOPES = [
    ("101", "Marketing"),
    ("201", "Output"),
    ("301", "Gratuities"),
    ("401", "Commercial equipment"),
    ("501", "Fixed assets"),
    ("601", "Own consumption"),
    ("703", "Delivery operations with installation"),
    ("704", "Transfer between managements"),
    ("705", "Goods made available to the customer"),
    ("801", "Financial/operational leasing"),
    ("802", "Goods under warranty"),
    ("901", "Exempt operations"),
    ("1001", "Investment in progress"),
    ("1101", "Donations, help"),
    ("9901", "Other"),
    ("9999", "Same with operation"),
]

OPERATION_TYPE_TO_ALLOWED_SCOPE_CODES = {
    "10": (
        "101",
        "201",
        "301",
        "401",
        "501",
        "601",
        "703",
        "801",
        "802",
        "901",
        "1001",
        "1101",
        "9901",
    ),
    "20": ("101", "301", "703", "801", "802", "9901"),
    "30": ("101", "704", "705", "9901"),
}

LOCATION_TYPES = [
    ("location", "Location"),
    ("bcp", "Border Crossing Point"),
    ("customs", "Customs Office"),
]

LOCATION_TYPE_MAP = {
    "start": {
        "customs_code": "40",
        "bcp_codes": ("10", "12", "14", "60"),
    },
    "end": {
        "customs_code": "50",
        "bcp_codes": ("10", "20", "22", "24", "70"),
    },
}

BORDER_CROSSING_POINTS = [
    ("1", "Petea (HU)"),
    ("2", "Borș(HU)"),
    ("3", "Vărșand(HU)"),
    ("4", "Nădlac(HU)"),
    ("5", "Calafat (BG)"),
    ("6", "Bechet(BG)"),
    ("7", "Turnu Măgurele(BG)"),
    ("8", "Zimnicea(BG)"),
    ("9", "Giurgiu(BG)"),
    ("10", "Ostrov(BG)"),
    ("11", "Negru Vodă(BG)"),
    ("12", "Vama Veche(BG)"),
    ("13", "Călărași(BG)"),
    ("14", "Corabia(BG)"),
    ("15", "Oltenița(BG)"),
    ("16", "Carei  (HU)"),
    ("17", "Cenad (HU)"),
    ("18", "Episcopia Bihor (HU)"),
    ("19", "Salonta (HU)"),
    ("20", "Săcuieni (HU)"),
    ("21", "Turnu (HU)"),
    ("22", "Urziceni (HU)"),
    ("23", "Valea lui Mihai (HU)"),
    ("24", "Vladimirescu (HU)"),
    ("25", "Porțile de Fier 1 (RS)"),
    ("26", "Naidăș(RS)"),
    ("27", "Stamora Moravița(RS)"),
    ("28", "Jimbolia(RS)"),
    ("29", "Halmeu (UA)"),
    ("30", "Stânca Costești (MD)"),
    ("31", "Sculeni(MD)"),
    ("32", "Albița(MD)"),
    ("33", "Oancea(MD)"),
    ("34", "Galați Giurgiulești(MD)"),
    ("35", "Constanța Sud Agigea"),
    ("36", "Siret  (UA)"),
    ("37", "Nădlac 2 - A1 (HU)"),
    ("38", "Borș 2 - A3 (HU)"),
]

CUSTOMS_OFFICES = [
    ("12801", "BVI Alba Iulia (ROBV0300)"),
    ("22801", "BVI Arad (ROTM0200)"),
    ("22901", "BVF Arad Aeroport (ROTM0230)"),
    ("22902", "BVF Zona Liberă Curtici (ROTM2300)"),
    ("32801", "BVI Pitești (ROCR7000)"),
    ("42801", "BVI Bacău (ROIS0600)"),
    ("42901", "BVF Bacău Aeroport (ROIS0620)"),
    ("52801", "BVI Oradea (ROCJ6570)"),
    ("52901", "BVF Oradea Aeroport (ROCJ6580)"),
    ("62801", "BVI Bistriţa-Năsăud (ROCJ0400)"),
    ("72801", "BVI Botoşani (ROIS1600)"),
    ("72901", "BVF Stanca Costeşti (ROIS1610)"),
    ("72902", "BVF Rădăuţi Prut (ROIS1620)"),
    ("82801", "BVI Braşov (ROBV0900)"),
    ("92901", "BVF Zona Liberă Brăila (ROGL0710)"),
    ("92902", "BVF Brăila (ROGL0700)"),
    ("102801", "BVI Buzău (ROGL1500)"),
    ("112801", "BVI Reșița (ROTM7600)"),
    ("112901", "BVF Naidăș (ROTM6100)"),
    ("122801", "BVI Cluj Napoca (ROCJ1800)"),
    ("122901", "BVF Cluj Napoca Aero (ROCJ1810)"),
    ("132901", "BVF Constanţa Sud Agigea (ROCT1900)"),
    ("132902", "BVF Mihail Kogălniceanu (ROCT5100)"),
    ("132903", "BVF Mangalia (ROCT5400)"),
    ("132904", "BVF Constanţa Port (ROCT1970)"),
    ("142801", "BVI Sfântu Gheorghe (ROBV7820)"),
    ("152801", "BVI Târgoviște (ROBU8600)"),
    ("162801", "BVI Craiova (ROCR2100)"),
    ("162901", "BVF Craiova Aeroport (ROCR2110)"),
    ("162902", "BVF Bechet (ROCR1720)"),
    ("162903", "BVF Calafat (ROCR1700)"),
    ("172901", "BVF Zona Liberă Galaţi (ROGL3810)"),
    ("172902", "BVF Giurgiuleşti (ROGL3850)"),
    ("172903", "BVF Oancea (ROGL3610)"),
    ("172904", "BVF Galaţi (ROGL3800)"),
    ("182801", "BVI Târgu Jiu (ROCR8810)"),
    ("192801", "BVI Miercurea Ciuc (ROBV5600)"),
    ("202801", "BVI Deva (ROTM8100)"),
    ("212801", "BVI Slobozia (ROCT8220)"),
    ("222901", "BVF Iaşi Aero (ROIS4660)"),
    ("222902", "BVF Sculeni (ROIS4990)"),
    ("222903", "BVF Iaşi (ROIS4650)"),
    ("232801", "BVI Antrepozite/Ilfov (ROBU1200)"),
    ("232901", "BVF Otopeni Călători (ROBU1030)"),
    ("242801", "BVI Baia Mare (ROCJ0500)"),
    ("242901", "BVF Aero Baia Mare (ROCJ0510)"),
    ("242902", "BVF Sighet (ROCJ8000)"),
    ("252901", "BVF Orşova (ROCR7280)"),
    ("252902", "BVF Porţile De Fier I (ROCR7270)"),
    ("252903", "BVF Porţile De Fier II (ROCR7200)"),
    ("252904", "BVF Drobeta Turnu Severin (ROCR9000)"),
    ("262801", "BVI Târgu Mureş (ROBV8800)"),
    ("262901", "BVF Târgu Mureş Aeroport (ROBV8820)"),
    ("272801", "BVI Piatra Neamţ (ROIS7400)"),
    ("282801", "BVI Corabia (ROCR2000)"),
    ("282802", "BVI Olt (ROCR8210)"),
    ("292801", "BVI Ploiești (ROBU7100)"),
    ("302801", "BVI Satu-Mare (ROCJ7810)"),
    ("302901", "BVF Halmeu (ROCJ4310)"),
    ("302902", "BVF Aeroport Satu Mare (ROCJ7830)"),
    ("312801", "BVI Zalău (ROCJ9700)"),
    ("322801", "BVI Sibiu (ROBV7900)"),
    ("322901", "BVF Sibiu Aeroport (ROBV7910)"),
    ("332801", "BVI Suceava (ROIS8230)"),
    ("332901", "BVF Dorneşti (ROIS2700)"),
    ("332902", "BVF Siret (ROIS8200)"),
    ("332903", "BVF Suceava Aero (ROIS8250)"),
    ("332904", "BVF Vicovu De Sus (ROIS9620)"),
    ("342801", "BVI Alexandria (ROCR0310)"),
    ("342901", "BVF Turnu Măgurele (ROCR9100)"),
    ("342902", "BVF Zimnicea (ROCR5800)"),
    ("352802", "BVI Timişoara Bază (ROTM8720)"),
    ("352901", "BVF Jimbolia (ROTM5010)"),
    ("352902", "BVF Moraviţa (ROTM5510)"),
    ("352903", "BVF Timişoara Aeroport (ROTM8730)"),
    ("362901", "BVF Sulina (ROCT8300)"),
    ("362902", "BVF Aeroport Delta Dunării Tulcea (ROGL8910)"),
    ("362903", "BVF Tulcea (ROGL8900)"),
    ("362904", "BVF Isaccea (ROGL8920)"),
    ("372801", "BVI Vaslui (ROIS9610)"),
    ("372901", "BVF Fălciu (-)"),
    ("372902", "BVF Albiţa (ROIS0100)"),
    ("382801", "BVI Râmnicu Vâlcea (ROCR7700)"),
    ("392801", "BVI Focșani (ROGL3600)"),
    ("402801", "BVI Bucureşti Poştă (ROBU1380)"),
    ("402802", "BVI Târguri și Expoziții (ROBU1400)"),
    ("402901", "BVF Băneasa (ROBU1040)"),
    ("512801", "BVI Călăraşi (ROCT1710)"),
    ("522801", "BVI Giurgiu (ROBU3910)"),
    ("522901", "BVF Zona Liberă Giurgiu (ROBU3980)"),
]

STATE_CODES = {
    "AB": "1",
    "AR": "2",
    "AG": "3",
    "BC": "4",
    "BH": "5",
    "BN": "6",
    "BT": "7",
    "BV": "8",
    "BR": "9",
    "BZ": "10",
    "CS": "11",
    "CJ": "12",
    "CT": "13",
    "CV": "14",
    "DB": "15",
    "DJ": "16",
    "GL": "17",
    "GJ": "18",
    "HR": "19",
    "HD": "20",
    "IL": "21",
    "IS": "22",
    "IF": "23",
    "MM": "24",
    "MH": "25",
    "MS": "26",
    "NT": "27",
    "OT": "28",
    "PH": "29",
    "SM": "30",
    "SJ": "31",
    "SB": "32",
    "SV": "33",
    "TR": "34",
    "TM": "35",
    "TL": "36",
    "VS": "37",
    "VL": "38",
    "VN": "39",
    "B": "40",
    "CL": "51",
    "GR": "52",
}

_eu_country_vat = {"GR": "EL"}


def _document_depends(model):
    # The one2many to l10n_ro_edi.document is declared by each host (its
    # inverse differs), and stock.picking.batch gets its own only once
    # l10n_ro_edi_stock_batch is loaded, so the dependency is stated where
    # the field exists rather than asserted for every host.
    depends = ["company_id.account_fiscal_country_id.code"]
    if "l10n_ro_edi_stock_document_ids" in model._fields:
        depends.append("l10n_ro_edi_stock_document_ids")
    return depends


_debug = DebugLog(__name__)


class MixinStockConsignment(models.AbstractModel):
    _inherit = "mixin.stock.consignment"

    l10n_ro_edi_stock_document_uit = fields.Char(
        string="eTransport UIT",
        compute="_compute_l10n_ro_edi_stock_current_document_uit",
    )
    l10n_ro_edi_stock_state = fields.Selection(
        selection=DOCUMENT_STATES,
        string="eTransport Status",
        compute="_compute_l10n_ro_edi_stock_current_document_state",
        store=True,
    )

    # Data fields
    l10n_ro_edi_stock_operation_type = fields.Selection(
        selection=OPERATION_TYPES,
        string="eTransport Operation Type",
    )
    l10n_ro_edi_stock_available_operation_scopes = fields.Char(
        compute="_compute_l10n_ro_edi_stock_available_operation_scopes"
    )
    l10n_ro_edi_stock_operation_scope = fields.Selection(
        selection=OPERATION_SCOPES,
        string="Operation Scope",
    )

    l10n_ro_edi_stock_vehicle_number = fields.Char(
        string="Vehicle Number",
        size=20,
    )
    l10n_ro_edi_stock_trailer_1_number = fields.Char(
        string="Trailer 1 Number",
        size=20,
    )
    l10n_ro_edi_stock_trailer_2_number = fields.Char(
        string="Trailer 2 Number",
        size=20,
    )

    l10n_ro_edi_stock_available_start_loc_types = fields.Char(
        compute="_compute_l10n_ro_edi_stock_available_location_types"
    )
    l10n_ro_edi_stock_start_loc_type = fields.Selection(
        selection=LOCATION_TYPES,
        string="Start Location Type",
        compute="_compute_l10n_ro_edi_stock_default_location_type",
        store=True,
        readonly=False,
    )

    l10n_ro_edi_stock_available_end_loc_types = fields.Char(
        compute="_compute_l10n_ro_edi_stock_available_location_types"
    )
    l10n_ro_edi_stock_end_loc_type = fields.Selection(
        selection=LOCATION_TYPES,
        string="End Location Type",
        compute="_compute_l10n_ro_edi_stock_default_location_type",
        store=True,
        readonly=False,
    )

    l10n_ro_edi_stock_start_bcp = fields.Selection(
        selection=BORDER_CROSSING_POINTS,
        string="Start Border Crossing Point",
    )
    l10n_ro_edi_stock_start_customs_office = fields.Selection(
        selection=CUSTOMS_OFFICES,
        string="Start Customs Office",
    )
    l10n_ro_edi_stock_end_bcp = fields.Selection(
        selection=BORDER_CROSSING_POINTS,
        string="End Border Crossing Point",
    )
    l10n_ro_edi_stock_end_customs_office = fields.Selection(
        selection=CUSTOMS_OFFICES,
        string="End Customs Office",
    )

    l10n_ro_edi_stock_remarks = fields.Text(string="Remarks")

    # View control fields
    l10n_ro_edi_stock_enable = fields.Boolean(
        compute="_compute_l10n_ro_edi_stock_enable"
    )
    l10n_ro_edi_stock_enable_send = fields.Boolean(
        compute="_compute_l10n_ro_edi_stock_enable_send"
    )
    l10n_ro_edi_stock_enable_fetch = fields.Boolean(
        compute="_compute_l10n_ro_edi_stock_enable_fetch"
    )
    l10n_ro_edi_stock_enable_amend = fields.Boolean(
        compute="_compute_l10n_ro_edi_stock_enable_amend"
    )

    l10n_ro_edi_stock_fields_readonly = fields.Boolean(
        compute="_compute_l10n_ro_edi_stock_fields_readonly"
    )

    @api.onchange("l10n_ro_edi_stock_operation_type")
    def _l10n_ro_edi_stock_reset_variable_selection_fields(self):
        _debug.lifecycle("etransport_fields_reset", records=self)
        self.l10n_ro_edi_stock_operation_scope = False

        # the 'location' value is always valid, regardless of which operation type is chosen
        self.l10n_ro_edi_stock_start_loc_type = "location"
        self.l10n_ro_edi_stock_end_loc_type = "location"

    @api.depends("company_id.account_fiscal_country_id.code")
    def _compute_l10n_ro_edi_stock_default_location_type(self):
        for record in self:
            if record.company_id.account_fiscal_country_id.code == "RO":
                record.l10n_ro_edi_stock_start_loc_type = (
                    record.l10n_ro_edi_stock_start_loc_type or "location"
                )
                record.l10n_ro_edi_stock_end_loc_type = (
                    record.l10n_ro_edi_stock_end_loc_type or "location"
                )
            else:
                record.l10n_ro_edi_stock_start_loc_type = False
                record.l10n_ro_edi_stock_end_loc_type = False

    @api.depends("l10n_ro_edi_stock_operation_type")
    def _compute_l10n_ro_edi_stock_available_operation_scopes(self):
        for record in self:
            if record.l10n_ro_edi_stock_operation_type:
                allowed_scopes = OPERATION_TYPE_TO_ALLOWED_SCOPE_CODES.get(
                    record.l10n_ro_edi_stock_operation_type, ("9999",)
                )
            else:
                allowed_scopes = [c for c, _dummy in OPERATION_SCOPES]

            record.l10n_ro_edi_stock_available_operation_scopes = ",".join(
                allowed_scopes
            )

    @api.depends("l10n_ro_edi_stock_operation_type")
    def _compute_l10n_ro_edi_stock_available_location_types(self):
        for record in self:
            record.l10n_ro_edi_stock_available_start_loc_types = (
                record._l10n_ro_edi_stock_get_available_location_types(
                    record.l10n_ro_edi_stock_operation_type, "start"
                )
            )
            record.l10n_ro_edi_stock_available_end_loc_types = (
                record._l10n_ro_edi_stock_get_available_location_types(
                    record.l10n_ro_edi_stock_operation_type, "end"
                )
            )

    @api.depends(_document_depends)
    def _compute_l10n_ro_edi_stock_current_document_state(self):
        for record in self:
            if record.company_id.account_fiscal_country_id.code == "RO" and (
                document := record._l10n_ro_edi_stock_get_current_document()
            ):
                record.l10n_ro_edi_stock_state = document.state
            else:
                record.l10n_ro_edi_stock_state = False

    @api.depends(_document_depends)
    def _compute_l10n_ro_edi_stock_current_document_uit(self):
        for record in self:
            if record.company_id.account_fiscal_country_id.code == "RO" and (
                document := record._l10n_ro_edi_stock_get_current_document()
            ):
                record.l10n_ro_edi_stock_document_uit = document.l10n_ro_edi_stock_uit
            else:
                record.l10n_ro_edi_stock_document_uit = False

    @api.depends("company_id.account_fiscal_country_id.code")
    def _compute_l10n_ro_edi_stock_enable(self):
        _debug.perf.count("etransport_enable_compute", records=self)
        for record in self:
            record.l10n_ro_edi_stock_enable = (
                record.company_id.account_fiscal_country_id.code == "RO"
            )

    @api.depends("l10n_ro_edi_stock_enable", "state", "l10n_ro_edi_stock_state")
    def _compute_l10n_ro_edi_stock_enable_send(self):
        for record in self:
            record.l10n_ro_edi_stock_enable_send = (
                record.l10n_ro_edi_stock_enable
                and record._l10n_ro_edi_stock_is_shipped()
                and record.l10n_ro_edi_stock_state in (False, "stock_sending_failed")
                and not record._l10n_ro_edi_stock_get_last_document("stock_validated")
            )

    @api.depends("l10n_ro_edi_stock_enable", "state", "l10n_ro_edi_stock_state")
    def _compute_l10n_ro_edi_stock_enable_fetch(self):
        for record in self:
            record.l10n_ro_edi_stock_enable_fetch = (
                record.l10n_ro_edi_stock_enable
                and record.l10n_ro_edi_stock_state == "stock_sent"
            )

    @api.depends("l10n_ro_edi_stock_state")
    def _compute_l10n_ro_edi_stock_enable_amend(self):
        for record in self:
            record.l10n_ro_edi_stock_enable_amend = (
                record.l10n_ro_edi_stock_enable
                and (
                    record.l10n_ro_edi_stock_state == "stock_validated"
                    or (
                        record.l10n_ro_edi_stock_state == "stock_sending_failed"
                        and record._l10n_ro_edi_stock_get_last_document(
                            "stock_validated"
                        )
                    )
                )
            )

    @api.depends("l10n_ro_edi_stock_state")
    def _compute_l10n_ro_edi_stock_fields_readonly(self):
        for record in self:
            record.l10n_ro_edi_stock_fields_readonly = (
                record.l10n_ro_edi_stock_state == "stock_sent"
            )

    def _l10n_ro_edi_stock_is_shipped(self) -> bool:
        raise NotImplementedError

    def _l10n_ro_edi_stock_get_current_document(self):
        self.check_singleton()
        return (
            self.l10n_ro_edi_stock_document_ids.sorted()[0]
            if self.l10n_ro_edi_stock_document_ids
            else None
        )

    def _l10n_ro_edi_stock_get_all_documents(self, states):
        self.check_singleton()

        if isinstance(states, str):
            states = [states]

        return self.l10n_ro_edi_stock_document_ids.filtered(
            lambda doc: doc.state in states
        )

    def _l10n_ro_edi_stock_get_last_document(self, state):
        self.check_singleton()
        documents_in_state = self.l10n_ro_edi_stock_document_ids.filtered(
            lambda doc: doc.state == state
        ).sorted()

        return documents_in_state and documents_in_state[0]

    @api.model
    def _l10n_ro_edi_stock_get_available_location_types(
        self, operation_type, location: Literal["start", "end"]
    ) -> str:
        if operation_type == LOCATION_TYPE_MAP[location]["customs_code"]:
            return "location,bcp,customs"
        elif operation_type in LOCATION_TYPE_MAP[location]["bcp_codes"]:
            return "location,bcp"
        else:
            return "location"
