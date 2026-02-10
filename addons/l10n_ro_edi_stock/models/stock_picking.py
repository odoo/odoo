from typing import Literal

import base64
import markupsafe
import requests

from odoo import api, fields, models, _
from odoo.addons.l10n_ro_edi_stock.models.l10n_ro_edi_stock_document import DOCUMENT_STATES
from odoo.addons.l10n_ro_edi_stock.models.etransport_api import ETransportAPI
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

OPERATION_TYPES = [
    ('10', "Intra-community purchase"),
    ('12', "Operations in lohn system (EU) - input"),
    ('14', "Stocks available to the customer (Call-off stock) - entry"),
    ('20', "Intra-Community delivery"),
    ('22', "Operations in lohn system (EU) - exit"),
    ('24', "Stocks available to the customer (Call-off stock) - exit"),
    ('30', "Transport on the national territory"),
    ('40', "Import"),
    ('50', "Export"),
    ('60', "Intra-community transaction - Entry for storage/formation of new transport"),
    ('70', "Intra-community transaction - Exit after storage/formation of new transport"),
]

OPERATION_SCOPES = [
    ('101', "Marketing"),
    ('201', "Output"),
    ('301', "Gratuities"),
    ('401', "Commercial equipment"),
    ('501', "Fixed assets"),
    ('601', "Own consumption"),
    ('703', "Delivery operations with installation"),
    ('704', "Transfer between managements"),
    ('705', "Goods made available to the customer"),
    ('801', "Financial/operational leasing"),
    ('802', "Goods under warranty"),
    ('901', "Exempt operations"),
    ('1001', "Investment in progress"),
    ('1101', "Donations, help"),
    ('9901', "Other"),
    ('9999', "Same with operation"),
]

OPERATION_TYPE_TO_ALLOWED_SCOPE_CODES = {
    "10": ("101", "201", "301", "401", "501", "601", "703", "801", "802", "901", "1001", "1101", "9901"),
    "20": ("101", "301", "703", "801", "802", "9901"),
    "30": ("101", "704", "705", "9901"),
}

LOCATION_TYPES = [('location', "Location"), ('bcp', "Border Crossing Point"), ('customs', "Customs Office")]

LOCATION_TYPE_MAP = {
    'start': {
        'customs_code': '40',
        'bcp_codes': ('10', '12', '14', '60'),
    },
    'end': {
        'customs_code': '50',
        'bcp_codes': ('10', '20', '22', '24', '70'),
    }
}

BORDER_CROSSING_POINTS = [
    ('1', "Petea (HU)"),
    ('2', "Borș(HU)"),
    ('3', "Vărșand(HU)"),
    ('4', "Nădlac(HU)"),
    ('5', "Calafat (BG)"),
    ('6', "Bechet(BG)"),
    ('7', "Turnu Măgurele(BG)"),
    ('8', "Zimnicea(BG)"),
    ('9', "Giurgiu(BG)"),
    ('10', "Ostrov(BG)"),
    ('11', "Negru Vodă(BG)"),
    ('12', "Vama Veche(BG)"),
    ('13', "Călărași(BG)"),
    ('14', "Corabia(BG)"),
    ('15', "Oltenița(BG)"),
    ('16', "Carei  (HU)"),
    ('17', "Cenad (HU)"),
    ('18', "Episcopia Bihor (HU)"),
    ('19', "Salonta (HU)"),
    ('20', "Săcuieni (HU)"),
    ('21', "Turnu (HU)"),
    ('22', "Urziceni (HU)"),
    ('23', "Valea lui Mihai (HU)"),
    ('24', "Vladimirescu (HU)"),
    ('25', "Porțile de Fier 1 (RS)"),
    ('26', "Naidăș(RS)"),
    ('27', "Stamora Moravița(RS)"),
    ('28', "Jimbolia(RS)"),
    ('29', "Halmeu (UA)"),
    ('30', "Stânca Costești (MD)"),
    ('31', "Sculeni(MD)"),
    ('32', "Albița(MD)"),
    ('33', "Oancea(MD)"),
    ('34', "Galați Giurgiulești(MD)"),
    ('35', "Constanța Sud Agigea"),
    ('36', "Siret  (UA)"),
    ('37', "Nădlac 2 - A1 (HU)"),
    ('38', "Borș 2 - A3 (HU)"),
]

CUSTOMS_OFFICES = [
    ('12801', "BVI Alba Iulia (ROBV0300)"),
    ('22801', "BVI Arad (ROTM0200)"),
    ('22901', "BVF Arad Aeroport (ROTM0230)"),
    ('22902', "BVF Zona Liberă Curtici (ROTM2300)"),
    ('32801', "BVI Pitești (ROCR7000)"),
    ('42801', "BVI Bacău (ROIS0600)"),
    ('42901', "BVF Bacău Aeroport (ROIS0620)"),
    ('52801', "BVI Oradea (ROCJ6570)"),
    ('52901', "BVF Oradea Aeroport (ROCJ6580)"),
    ('62801', "BVI Bistriţa-Năsăud (ROCJ0400)"),
    ('72801', "BVI Botoşani (ROIS1600)"),
    ('72901', "BVF Stanca Costeşti (ROIS1610)"),
    ('72902', "BVF Rădăuţi Prut (ROIS1620)"),
    ('82801', "BVI Braşov (ROBV0900)"),
    ('92901', "BVF Zona Liberă Brăila (ROGL0710)"),
    ('92902', "BVF Brăila (ROGL0700)"),
    ('102801', "BVI Buzău (ROGL1500)"),
    ('112801', "BVI Reșița (ROTM7600)"),
    ('112901', "BVF Naidăș (ROTM6100)"),
    ('122801', "BVI Cluj Napoca (ROCJ1800)"),
    ('122901', "BVF Cluj Napoca Aero (ROCJ1810)"),
    ('132901', "BVF Constanţa Sud Agigea (ROCT1900)"),
    ('132902', "BVF Mihail Kogălniceanu (ROCT5100)"),
    ('132903', "BVF Mangalia (ROCT5400)"),
    ('132904', "BVF Constanţa Port (ROCT1970)"),
    ('142801', "BVI Sfântu Gheorghe (ROBV7820)"),
    ('152801', "BVI Târgoviște (ROBU8600)"),
    ('162801', "BVI Craiova (ROCR2100)"),
    ('162901', "BVF Craiova Aeroport (ROCR2110)"),
    ('162902', "BVF Bechet (ROCR1720)"),
    ('162903', "BVF Calafat (ROCR1700)"),
    ('172901', "BVF Zona Liberă Galaţi (ROGL3810)"),
    ('172902', "BVF Giurgiuleşti (ROGL3850)"),
    ('172903', "BVF Oancea (ROGL3610)"),
    ('172904', "BVF Galaţi (ROGL3800)"),
    ('182801', "BVI Târgu Jiu (ROCR8810)"),
    ('192801', "BVI Miercurea Ciuc (ROBV5600)"),
    ('202801', "BVI Deva (ROTM8100)"),
    ('212801', "BVI Slobozia (ROCT8220)"),
    ('222901', "BVF Iaşi Aero (ROIS4660)"),
    ('222902', "BVF Sculeni (ROIS4990)"),
    ('222903', "BVF Iaşi (ROIS4650)"),
    ('232801', "BVI Antrepozite/Ilfov (ROBU1200)"),
    ('232901', "BVF Otopeni Călători (ROBU1030)"),
    ('242801', "BVI Baia Mare (ROCJ0500)"),
    ('242901', "BVF Aero Baia Mare (ROCJ0510)"),
    ('242902', "BVF Sighet (ROCJ8000)"),
    ('252901', "BVF Orşova (ROCR7280)"),
    ('252902', "BVF Porţile De Fier I (ROCR7270)"),
    ('252903', "BVF Porţile De Fier II (ROCR7200)"),
    ('252904', "BVF Drobeta Turnu Severin (ROCR9000)"),
    ('262801', "BVI Târgu Mureş (ROBV8800)"),
    ('262901', "BVF Târgu Mureş Aeroport (ROBV8820)"),
    ('272801', "BVI Piatra Neamţ (ROIS7400)"),
    ('282801', "BVI Corabia (ROCR2000)"),
    ('282802', "BVI Olt (ROCR8210)"),
    ('292801', "BVI Ploiești (ROBU7100)"),
    ('302801', "BVI Satu-Mare (ROCJ7810)"),
    ('302901', "BVF Halmeu (ROCJ4310)"),
    ('302902', "BVF Aeroport Satu Mare (ROCJ7830)"),
    ('312801', "BVI Zalău (ROCJ9700)"),
    ('322801', "BVI Sibiu (ROBV7900)"),
    ('322901', "BVF Sibiu Aeroport (ROBV7910)"),
    ('332801', "BVI Suceava (ROIS8230)"),
    ('332901', "BVF Dorneşti (ROIS2700)"),
    ('332902', "BVF Siret (ROIS8200)"),
    ('332903', "BVF Suceava Aero (ROIS8250)"),
    ('332904', "BVF Vicovu De Sus (ROIS9620)"),
    ('342801', "BVI Alexandria (ROCR0310)"),
    ('342901', "BVF Turnu Măgurele (ROCR9100)"),
    ('342902', "BVF Zimnicea (ROCR5800)"),
    ('352802', "BVI Timişoara Bază (ROTM8720)"),
    ('352901', "BVF Jimbolia (ROTM5010)"),
    ('352902', "BVF Moraviţa (ROTM5510)"),
    ('352903', "BVF Timişoara Aeroport (ROTM8730)"),
    ('362901', "BVF Sulina (ROCT8300)"),
    ('362902', "BVF Aeroport Delta Dunării Tulcea (ROGL8910)"),
    ('362903', "BVF Tulcea (ROGL8900)"),
    ('362904', "BVF Isaccea (ROGL8920)"),
    ('372801', "BVI Vaslui (ROIS9610)"),
    ('372901', "BVF Fălciu (-)"),
    ('372902', "BVF Albiţa (ROIS0100)"),
    ('382801', "BVI Râmnicu Vâlcea (ROCR7700)"),
    ('392801', "BVI Focșani (ROGL3600)"),
    ('402801', "BVI Bucureşti Poştă (ROBU1380)"),
    ('402802', "BVI Târguri și Expoziții (ROBU1400)"),
    ('402901', "BVF Băneasa (ROBU1040)"),
    ('512801', "BVI Călăraşi (ROCT1710)"),
    ('522801', "BVI Giurgiu (ROBU3910)"),
    ('522901', "BVF Zona Liberă Giurgiu (ROBU3980)"),
]

STATE_CODES = {
    'AB': '1',
    'AR': '2',
    'AG': '3',
    'BC': '4',
    'BH': '5',
    'BN': '6',
    'BT': '7',
    'BV': '8',
    'BR': '9',
    'BZ': '10',
    'CS': '11',
    'CJ': '12',
    'CT': '13',
    'CV': '14',
    'DB': '15',
    'DJ': '16',
    'GL': '17',
    'GJ': '18',
    'HR': '19',
    'HD': '20',
    'IL': '21',
    'IS': '22',
    'IF': '23',
    'MM': '24',
    'MH': '25',
    'MS': '26',
    'NT': '27',
    'OT': '28',
    'PH': '29',
    'SM': '30',
    'SJ': '31',
    'SB': '32',
    'SV': '33',
    'TR': '34',
    'TM': '35',
    'TL': '36',
    'VS': '37',
    'VL': '38',
    'VN': '39',
    'B': '40',
    'CL': '51',
    'GR': '52',
}

_eu_country_vat = {
    'GR': 'EL'
}


class Picking(models.Model):
    _inherit = 'stock.picking'

    # Document fields
    l10n_ro_edi_stock_document_ids = fields.One2many(comodel_name='l10n_ro_edi.document', inverse_name='picking_id')
    l10n_ro_edi_stock_document_uit = fields.Char(compute='_compute_l10n_ro_edi_stock_current_document_uit', string="eTransport UIT")
    l10n_ro_edi_stock_state = fields.Selection(
        selection=DOCUMENT_STATES,
        compute='_compute_l10n_ro_edi_stock_current_document_state',
        string="eTransport Status",
        store=True,
    )

    # Data fields
    l10n_ro_edi_stock_operation_type = fields.Selection(selection=OPERATION_TYPES, string="eTransport Operation Type")
    l10n_ro_edi_stock_available_operation_scopes = fields.Char(compute='_compute_l10n_ro_edi_stock_available_operation_scopes')
    l10n_ro_edi_stock_operation_scope = fields.Selection(selection=OPERATION_SCOPES, string="Operation Scope")

    l10n_ro_edi_stock_vehicle_number = fields.Char(string="Vehicle Number", size=20)
    l10n_ro_edi_stock_trailer_1_number = fields.Char(string="Trailer 1 Number", size=20)
    l10n_ro_edi_stock_trailer_2_number = fields.Char(string="Trailer 2 Number", size=20)

    l10n_ro_edi_stock_available_start_loc_types = fields.Char(compute='_compute_l10n_ro_edi_stock_available_location_types')
    l10n_ro_edi_stock_start_loc_type = fields.Selection(
        selection=LOCATION_TYPES,
        string="Start Location Type",
        compute='_compute_l10n_ro_edi_stock_default_location_type',
        store=True,
        readonly=False,
    )

    l10n_ro_edi_stock_available_end_loc_types = fields.Char(compute='_compute_l10n_ro_edi_stock_available_location_types')
    l10n_ro_edi_stock_end_loc_type = fields.Selection(
        selection=LOCATION_TYPES,
        string="End Location Type",
        compute='_compute_l10n_ro_edi_stock_default_location_type',
        store=True,
        readonly=False,
    )

    l10n_ro_edi_stock_start_bcp = fields.Selection(selection=BORDER_CROSSING_POINTS, string="Start Border Crossing Point")
    l10n_ro_edi_stock_start_customs_office = fields.Selection(selection=CUSTOMS_OFFICES, string="Start Customs Office")
    l10n_ro_edi_stock_end_bcp = fields.Selection(selection=BORDER_CROSSING_POINTS, string="End Border Crossing Point")
    l10n_ro_edi_stock_end_customs_office = fields.Selection(selection=CUSTOMS_OFFICES, string="End Customs Office")

    l10n_ro_edi_stock_remarks = fields.Text(string="Remarks")

    # View control fields
    l10n_ro_edi_stock_enable = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable')
    l10n_ro_edi_stock_enable_send = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable_send')
    l10n_ro_edi_stock_enable_fetch = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable_fetch')
    l10n_ro_edi_stock_enable_amend = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable_amend')

    l10n_ro_edi_stock_fields_readonly = fields.Boolean(compute='_compute_l10n_ro_edi_stock_fields_readonly')

    ################################################################################
    # Onchange Methods
    ################################################################################

    @api.onchange('l10n_ro_edi_stock_operation_type')
    def _l10n_ro_edi_stock_reset_variable_selection_fields(self):
        self.l10n_ro_edi_stock_operation_scope = False

        # the 'location' value is always valid, regardless of which operation type is chosen
        self.l10n_ro_edi_stock_start_loc_type = 'location'
        self.l10n_ro_edi_stock_end_loc_type = 'location'

    ################################################################################
    # Compute Methods
    ################################################################################

    @api.depends('company_id.account_fiscal_country_id.code')
    def _compute_l10n_ro_edi_stock_default_location_type(self):
        for picking in self:
            if picking.company_id.account_fiscal_country_id.code == 'RO':
                if not picking.l10n_ro_edi_stock_start_loc_type:
                    picking.l10n_ro_edi_stock_start_loc_type = 'location'
                else:
                    picking.l10n_ro_edi_stock_start_loc_type = picking.l10n_ro_edi_stock_start_loc_type

                if not picking.l10n_ro_edi_stock_end_loc_type:
                    picking.l10n_ro_edi_stock_end_loc_type = 'location'
                else:
                    picking.l10n_ro_edi_stock_end_loc_type = picking.l10n_ro_edi_stock_end_loc_type
            else:
                picking.l10n_ro_edi_stock_start_loc_type = False
                picking.l10n_ro_edi_stock_end_loc_type = False

    @api.depends('l10n_ro_edi_stock_operation_type')
    def _compute_l10n_ro_edi_stock_available_operation_scopes(self):
        for picking in self:
            if picking.l10n_ro_edi_stock_operation_type:
                allowed_scopes = OPERATION_TYPE_TO_ALLOWED_SCOPE_CODES.get(picking.l10n_ro_edi_stock_operation_type, ("9999",))
            else:
                allowed_scopes = [c for c, _dummy in OPERATION_SCOPES]

            picking.l10n_ro_edi_stock_available_operation_scopes = ','.join(allowed_scopes)

    @api.depends('l10n_ro_edi_stock_operation_type')
    def _compute_l10n_ro_edi_stock_available_location_types(self):
        for picking in self:
            picking.l10n_ro_edi_stock_available_start_loc_types = picking._l10n_ro_edi_stock_get_available_location_types(picking.l10n_ro_edi_stock_operation_type, 'start')
            picking.l10n_ro_edi_stock_available_end_loc_types = picking._l10n_ro_edi_stock_get_available_location_types(picking.l10n_ro_edi_stock_operation_type, 'end')

    @api.depends('l10n_ro_edi_stock_document_ids', 'company_id.account_fiscal_country_id.code')
    def _compute_l10n_ro_edi_stock_current_document_state(self):
        for picking in self:
            if picking.company_id.account_fiscal_country_id.code == 'RO' and (document := picking._l10n_ro_edi_stock_get_current_document()):
                picking.l10n_ro_edi_stock_state = document.state
            else:
                picking.l10n_ro_edi_stock_state = False

    @api.depends('l10n_ro_edi_stock_document_ids', 'company_id.account_fiscal_country_id.code')
    def _compute_l10n_ro_edi_stock_current_document_uit(self):
        for picking in self:
            if picking.company_id.account_fiscal_country_id.code == 'RO' and (document := picking._l10n_ro_edi_stock_get_current_document()):
                picking.l10n_ro_edi_stock_document_uit = document.l10n_ro_edi_stock_uit
            else:
                picking.l10n_ro_edi_stock_document_uit = False

    @api.depends('company_id.account_fiscal_country_id.code')
    def _compute_l10n_ro_edi_stock_enable(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable = picking.picking_type_code != 'internal' and picking.company_id.account_fiscal_country_id.code == 'RO'

    @api.depends('l10n_ro_edi_stock_enable', 'state', 'l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_enable_send(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable_send = (
                    picking.l10n_ro_edi_stock_enable
                    and picking.state == 'done'
                    and picking.l10n_ro_edi_stock_state in (False, 'stock_sending_failed')
                    and not picking._l10n_ro_edi_stock_get_last_document('stock_validated')
            )

    @api.depends('company_id', 'state', 'l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_enable_fetch(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable_fetch = picking.l10n_ro_edi_stock_enable and picking.l10n_ro_edi_stock_state == 'stock_sent'

    @api.depends('l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_enable_amend(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable_amend = picking.l10n_ro_edi_stock_enable and (
                    picking.l10n_ro_edi_stock_state == 'stock_validated'
                    or (
                        picking.l10n_ro_edi_stock_state == 'stock_sending_failed'
                        and picking._l10n_ro_edi_stock_get_last_document('stock_validated')
                    )
            )

    @api.depends('l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_fields_readonly(self):
        for picking in self:
            picking.l10n_ro_edi_stock_fields_readonly = picking.l10n_ro_edi_stock_state == 'stock_sent'

    ################################################################################
    # Validation methods
    ################################################################################

    def button_validate(self):
        # EXTENDS 'stock'

        # Validate the carrier first because it cannot be changed after the super call
        self._l10n_ro_edi_stock_validate_carrier()

        return super().button_validate()

    def _l10n_ro_edi_stock_validate_carrier(self):
        for picking in self.filtered(self._l10n_ro_edi_stock_validate_carrier_filter):
            # validate carrier
            if not picking.carrier_id:
                raise UserError(_("The picking %(picking_name)s is missing a delivery carrier.", picking_name=picking.name))

            # validate carrier partner
            if not picking.carrier_id.l10n_ro_edi_stock_partner_id:
                raise UserError(_("The delivery carrier of %(picking_name)s is missing the partner field value.", picking_name=picking.name))

    @api.model
    def _l10n_ro_edi_stock_validate_carrier_filter(self, picking):
        # To be overridden by stock.picking.batch
        return picking.l10n_ro_edi_stock_enable

    @api.model
    def _l10n_ro_edi_stock_validate_data(self, data: dict):
        errors = []

        # API access token
        if not data['company_id'].l10n_ro_edi_access_token:
            errors.append(_('Romanian access token not found. Please generate or fill it in the settings.'))

        # carrier partner fields
        partner = data['transport_partner_id']
        missing_carrier_partner_fields = []

        if not partner.vat:
            missing_carrier_partner_fields.append(_("VAT"))

        if not partner.city:
            missing_carrier_partner_fields.append(_("City"))

        if not partner.street:
            missing_carrier_partner_fields.append(_("Street"))

        if len(missing_carrier_partner_fields) == 1:
            errors.append(_("The delivery carrier partner is missing the %(field_name)s field.", field_name=missing_carrier_partner_fields[0]))
        elif len(missing_carrier_partner_fields) > 1:
            errors.append(_("The delivery carrier partner is missing following fields: %(field_names)s", field_names=', '.join(missing_carrier_partner_fields)))

        # operation type
        if not data['l10n_ro_edi_stock_operation_type']:
            errors.append(_("Operation type is missing."))
            return errors  # return prematurely because a lot of fields depend on the operation type

        # operation scope
        if not data['l10n_ro_edi_stock_operation_scope']:
            errors.append(_("Operation scope is missing."))

        # vehicle & trailer numbers
        if not data['l10n_ro_edi_stock_vehicle_number']:
            errors.append(_("Vehicle number is missing."))

        # All filled-in vehicle and trailer numbers must be unique
        license_plates = [num for num in (data['l10n_ro_edi_stock_vehicle_number'], data['l10n_ro_edi_stock_trailer_1_number'], data['l10n_ro_edi_stock_trailer_2_number']) if num]
        if len(license_plates) != len(set(license_plates)):
            errors.append(_("Vehicle number and trailer number fields must be unique."))

        # rate codes
        if 'intrastat_code_id' in self.env['product.product']._fields and data['l10n_ro_edi_stock_operation_type'] not in ('60', '70'):
            product_without_code_names = {move_line.product_id.name
                                          for move in data['stock_move_ids']
                                          for move_line in move.move_line_ids
                                          if not move_line.product_id.intrastat_code_id.code}

            if product_without_code_names:
                if len(product_without_code_names) == 1:
                    (product_name,) = product_without_code_names
                    errors.append(_("Product %(name)s is missing the intrastat code value.", name=product_name))
                else:
                    errors.append(_("Products %(names)s are missing the intrastat code value.", names=", ".join(product_without_code_names)))

        # Location types
        if not data['l10n_ro_edi_stock_start_loc_type']:
            if not data['l10n_ro_edi_stock_end_loc_type']:
                errors.append(_("Both 'End' and 'Start Location Type' are missing"))
            else:
                errors.append(_("'Start Location Type' is missing"))

            return errors  # return prematurely because all the start location fields depend on this field

        if not data['l10n_ro_edi_stock_end_loc_type']:
            errors.append(_("'End Location Type' is missing"))
            return errors  # return prematurely because all the end location fields depend on this field

        # Location fields
        for location in ('start', 'end'):
            loc_value = data[f'l10n_ro_edi_stock_{location}_loc_type']
            loc_group = _("'Start Location'") if location == 'start' else _("'End Location'")

            if loc_value == 'bcp' and not data[f'l10n_ro_edi_stock_{location}_bcp']:
                errors.append(_("The border crossing point is missing under %(location_group)s", location_group=loc_group))
            elif loc_value == 'customs' and not data[f'l10n_ro_edi_stock_{location}_customs_office']:
                errors.append(_("The customs office is missing under %(location_group)s", location_group=loc_group))
            elif loc_value == 'location':
                match data['picking_type_id'].code:
                    case 'outgoing':
                        partner = data['picking_type_id'].warehouse_id.partner_id if location == 'start' else data['partner_id']
                    case 'incoming':
                        partner = data['picking_type_id'].warehouse_id.partner_id if location == 'end' else data['partner_id']
                    case _other:
                        errors.append(_("Invalid picking type %(type_code)s", type_code=_other))
                        continue

                missing_field_names = []
                if not partner.state_id:
                    missing_field_names.append(_("State"))
                if not partner.city:
                    missing_field_names.append(_("City"))
                if not partner.street:
                    missing_field_names.append(_("Street"))
                if not partner.zip:
                    missing_field_names.append(_("Postal Code"))

                if len(missing_field_names) == 1:
                    errors.append(_("%(location_group)s is missing the %(field_name)s field.", location_group=loc_group, field_name=missing_field_names[0]))
                elif len(missing_field_names) > 1:
                    errors.append(_("%(location_group)s is missing following fields: %(field_names)s", location_group=loc_group, field_names=missing_field_names))

        return errors

    def _l10n_ro_edi_stock_validate_fetch_data(self, errors=None):
        if errors is None:
            errors = []
        self.ensure_one()

        if not self.company_id.l10n_ro_edi_access_token:
            errors.append(_('Romanian access token not found. Please generate or fill it in the settings.'))
            return errors

        match self.l10n_ro_edi_stock_state:
            case 'stock_sending_failed':
                if not self._l10n_ro_edi_stock_get_last_document('stock_validated'):
                    errors.append(_("This document has not been successfully sent yet because it contains errors."))
                else:
                    errors.append(_("This document has not been corrected yet because it contains errors."))
            case 'stock_validated':
                errors.append(_("This document has already been successfully sent to anaf."))

        return errors

    ################################################################################
    # Actions
    ################################################################################

    def action_l10n_ro_edi_stock_send_etransport(self):
        self.ensure_one()

        send_type = self.env.context.get('l10n_ro_edi_stock_send_type', 'send')
        self._l10n_ro_edi_stock_send_etransport_document(send_type=send_type)

    def action_l10n_ro_edi_stock_fetch_status(self):
        self._l10n_ro_edi_stock_fetch_document_status()

    ################################################################################
    # Document Helpers
    ################################################################################

    def _l10n_ro_edi_stock_get_current_document(self):
        """
        Returns the most recently created document in l10n_ro_edi_stock_document_ids
        """
        self.ensure_one()
        return self.l10n_ro_edi_stock_document_ids.sorted()[0] if self.l10n_ro_edi_stock_document_ids else None

    def _l10n_ro_edi_stock_get_all_documents(self, states):
        """
        Returns filtered documents by state
        """
        self.ensure_one()

        if isinstance(states, str):
            states = [states]

        return self.l10n_ro_edi_stock_document_ids.filtered(lambda doc: doc.state in states)

    def _l10n_ro_edi_stock_get_last_document(self, state):
        """
        Returns the most recently created document with the given state
        """
        self.ensure_one()
        documents_in_state = self.l10n_ro_edi_stock_document_ids.filtered(lambda doc: doc.state == state).sorted()

        return documents_in_state and documents_in_state[0]

    def _l10n_ro_edi_stock_create_document_stock_sent(self, values: dict[str, object]):
        self.ensure_one()
        return self.env['l10n_ro_edi.document'].create({
            'picking_id': self.id,
            'state': 'stock_sent',
            'l10n_ro_edi_stock_load_id': values['l10n_ro_edi_stock_load_id'],
            'l10n_ro_edi_stock_uit': values['l10n_ro_edi_stock_uit'],
            'attachment': base64.b64encode(values['raw_xml'].encode('utf-8')),
        })

    def _l10n_ro_edi_stock_create_document_stock_sending_failed(self, values: dict[str, object]):
        self.ensure_one()
        document = self.env['l10n_ro_edi.document'].create({
            'picking_id': self.id,
            'state': 'stock_sending_failed',
            'message': values['message'],
            'l10n_ro_edi_stock_load_id': values.get('l10n_ro_edi_stock_load_id'),
            'l10n_ro_edi_stock_uit': values.get('l10n_ro_edi_stock_uit'),
        })

        if 'raw_xml' in values:
            # when an error is thrown during data validation there will be no 'raw_xml'
            document.attachment = base64.b64encode(values['raw_xml'].encode('utf-8'))

        return document

    def _l10n_ro_edi_stock_create_document_stock_validated(self, values: dict[str, object]):
        self.ensure_one()
        return self.env['l10n_ro_edi.document'].create({
            'picking_id': self.id,
            'state': 'stock_validated',
            'l10n_ro_edi_stock_load_id': values['l10n_ro_edi_stock_load_id'],
            'l10n_ro_edi_stock_uit': values['l10n_ro_edi_stock_uit'],
            'attachment': base64.b64encode(values['raw_xml'].encode('utf-8')),
        })

    ################################################################################
    # Send Logic
    ################################################################################

    def _l10n_ro_edi_stock_send_etransport_document(self, send_type: str):
        """
        Send the eTransport document to anaf
        :param send_type: 'send' (initial sending of document) | 'amend' (correct the already sent document)
        """
        self.ensure_one()

        data = {
            'partner_id': self.partner_id,
            'transport_partner_id': self.carrier_id.l10n_ro_edi_stock_partner_id,
            'company_id': self.company_id,
            'scheduled_date': self.scheduled_date,
            'name': self.name,
            'send_type': send_type,
            'l10n_ro_edi_stock_operation_type': self.l10n_ro_edi_stock_operation_type,
            'l10n_ro_edi_stock_operation_scope': self.l10n_ro_edi_stock_operation_scope,
            'stock_move_ids': self.move_ids,
            'l10n_ro_edi_stock_vehicle_number': self.l10n_ro_edi_stock_vehicle_number,
            'l10n_ro_edi_stock_trailer_1_number': self.l10n_ro_edi_stock_trailer_1_number,
            'l10n_ro_edi_stock_trailer_2_number': self.l10n_ro_edi_stock_trailer_2_number,
            'l10n_ro_edi_stock_start_loc_type': self.l10n_ro_edi_stock_start_loc_type,
            'l10n_ro_edi_stock_end_loc_type': self.l10n_ro_edi_stock_end_loc_type,
            'l10n_ro_edi_stock_remarks': self.l10n_ro_edi_stock_remarks,
            'picking_type_id': self.picking_type_id,
            'l10n_ro_edi_stock_start_bcp': self.l10n_ro_edi_stock_start_bcp,
            'l10n_ro_edi_stock_end_bcp': self.l10n_ro_edi_stock_end_bcp,
            'l10n_ro_edi_stock_start_customs_office': self.l10n_ro_edi_stock_start_customs_office,
            'l10n_ro_edi_stock_end_customs_office': self.l10n_ro_edi_stock_end_customs_office,
            'l10n_ro_edi_stock_document_uit': self.l10n_ro_edi_stock_document_uit,
        }

        if errors := self._l10n_ro_edi_stock_validate_data(data=data):
            document_values = {'message': '\n'.join(errors)}

            if send_type == 'amend':
                last_sent_document = self._l10n_ro_edi_stock_get_last_document('stock_validated')
                document_values |= {
                    'l10n_ro_edi_stock_load_id': last_sent_document.l10n_ro_edi_stock_load_id,
                    'l10n_ro_edi_stock_uit': last_sent_document.l10n_ro_edi_stock_uit,
                    'raw_xml': base64.b64decode(last_sent_document.attachment).decode(),
                }

            self._l10n_ro_edi_stock_create_document_stock_sending_failed(document_values)
            return

        raw_xml = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>\n") + self.env['ir.qweb']._render(
            'l10n_ro_edi_stock.l10n_ro_template_etransport',
            values=self._l10n_ro_edi_stock_get_template_data(data=data),
        )

        result = ETransportAPI().upload_data(company_id=self.company_id, data=raw_xml)

        if 'error' in result:
            document_values = {'message': result['error'], 'raw_xml': raw_xml}

            if send_type == 'amend':
                last_sent_document = self._l10n_ro_edi_stock_get_last_document('stock_validated')
                document_values |= {
                    'l10n_ro_edi_stock_load_id': last_sent_document.l10n_ro_edi_stock_load_id,
                    'l10n_ro_edi_stock_uit': last_sent_document.l10n_ro_edi_stock_uit,
                }

            self._l10n_ro_edi_stock_create_document_stock_sending_failed(document_values)
        else:
            self._l10n_ro_edi_stock_get_all_documents({'stock_sending_failed', 'stock_sent'}).unlink()

            content = result['content']

            if send_type == 'send':
                uit = content['UIT']
            else:
                last_validated = self._l10n_ro_edi_stock_get_last_document('stock_validated')
                uit = last_validated.l10n_ro_edi_stock_uit

            edi_document = self._l10n_ro_edi_stock_create_document_stock_sent({
                'l10n_ro_edi_stock_load_id': content['index_incarcare'],
                'l10n_ro_edi_stock_uit': uit,
                'raw_xml': raw_xml,
            })
            attachment = self.env['ir.attachment'].create({
                'name': f"etransport_{self.name.replace('/', '_')}.xml",
                'type': 'binary',
                'datas': edi_document.attachment,
            })
            self._message_log(
                body=_(
                    "Generated eTransport XML (UIT: %(uit)s) was sent to the authority.",
                    uit=uit,
                ),
                attachment_ids=attachment.ids
            )

    def _l10n_ro_edi_stock_fetch_document_status(self):
        session = requests.Session()
        documents_to_delete = self.env['l10n_ro_edi.document']
        to_fetch = self.filtered(lambda p: p.l10n_ro_edi_stock_state == 'stock_sent')

        for picking in to_fetch:
            current_sending_document = picking.l10n_ro_edi_stock_document_ids.filtered(lambda doc: doc.state == 'stock_sent')[0]

            if errors := picking._l10n_ro_edi_stock_validate_fetch_data():
                picking._l10n_ro_edi_stock_create_document_stock_sending_failed({
                    'message': '\n'.join(errors),
                    'l10n_ro_edi_stock_load_id': current_sending_document.l10n_ro_edi_stock_load_id,
                    'l10n_ro_edi_stock_uit': current_sending_document.l10n_ro_edi_stock_uit,
                    'raw_xml': base64.b64decode(current_sending_document.attachment).decode(),
                })
                continue

            result = ETransportAPI().get_status(
                company_id=picking.company_id,
                document_load_id=current_sending_document.l10n_ro_edi_stock_load_id,
                session=session,
            )

            if 'error' in result:
                picking._l10n_ro_edi_stock_create_document_stock_sending_failed({
                    'message': result['error'],
                    'l10n_ro_edi_stock_load_id': current_sending_document.l10n_ro_edi_stock_load_id,
                    'l10n_ro_edi_stock_uit': current_sending_document.l10n_ro_edi_stock_uit,
                    'raw_xml': base64.b64decode(current_sending_document.attachment).decode(),
                })
            else:
                documents_to_delete |= picking._l10n_ro_edi_stock_get_all_documents(('stock_sent', 'stock_sending_failed'))
                new_document_data = {
                    'l10n_ro_edi_stock_load_id': current_sending_document.l10n_ro_edi_stock_load_id,
                    'l10n_ro_edi_stock_uit': current_sending_document.l10n_ro_edi_stock_uit,
                    'raw_xml': base64.b64decode(current_sending_document.attachment).decode(),
                }
                match state := result['content']['stare']:
                    case 'ok':
                        picking._l10n_ro_edi_stock_create_document_stock_validated(new_document_data)
                    case 'in prelucrare':
                        # Document is still being validated
                        picking._l10n_ro_edi_stock_create_document_stock_sent(new_document_data)
                    case 'XML cu erori nepreluat de sistem':
                        new_document_data['message'] = _("XML contains errors.")
                        picking._l10n_ro_edi_stock_create_document_stock_sending_failed(new_document_data)
                    case _:
                        picking._l10n_ro_edi_stock_report_unhandled_document_state(state)

        documents_to_delete.unlink()

    ################################################################################
    # Template helpers
    ################################################################################

    @api.model
    def _l10n_ro_edi_stock_get_template_data(self, data: dict):
        """
        Returns the data necessary to render the eTransport template
        """
        commercial_partner = data['partner_id'].commercial_partner_id
        transport_partner = data['transport_partner_id']
        company_id = data['company_id']
        scheduled_date = data['scheduled_date'].date()
        name = data['name']
        commercial_partner_code = None

        if commercial_partner.vat:
            commercial_partner_code = self._l10n_ro_edi_stock_get_cod(commercial_partner)
        elif self.l10n_ro_edi_stock_operation_type == '30':
            commercial_partner_code = 'PF'

        template_data = {
            'send_type': data['send_type'],
            'codDeclarant': self._l10n_ro_edi_stock_get_cod(company_id),
            'refDeclarant': name,
            'notificare': {
                'codTipOperatiune': data['l10n_ro_edi_stock_operation_type'],
                'bunuriTransportate': [
                    {
                        'codScopOperatiune': data['l10n_ro_edi_stock_operation_scope'],
                        'codTarifar': (product.intrastat_code_id.code if 'intrastat_code_id' in product._fields else None) or '00000000',
                        'denumireMarfa': product.name,
                        'cantitate': float_round(move.product_qty, precision_digits=2),
                        'codUnitateMasura': move.product_uom._get_unece_code(),
                        'greutateNeta': float_round(move.weight, precision_digits=2),
                        'greutateBruta': float_round(self._l10n_ro_edi_stock_get_gross_weight(move), precision_digits=2),
                        'valoareLeiFaraTva': float_round(product.standard_price, precision_digits=2),
                    }
                    for move in data['stock_move_ids'] for product in move.product_id
                ],
                'partenerComercial': {
                    'codTara': _eu_country_vat.get(commercial_partner.country_code, commercial_partner.country_code),
                    'denumire': commercial_partner.name,
                    'cod': commercial_partner_code,
                },
                'dateTransport': {
                    'nrVehicul': data['l10n_ro_edi_stock_vehicle_number'].upper(),
                    'nrRemorca1': data['l10n_ro_edi_stock_trailer_1_number'].upper() if data['l10n_ro_edi_stock_trailer_1_number'] else None,
                    'nrRemorca2': data['l10n_ro_edi_stock_trailer_2_number'].upper() if data['l10n_ro_edi_stock_trailer_2_number'] else None,
                    'codTaraOrgTransport': _eu_country_vat.get(transport_partner.country_code, transport_partner.country_code),
                    'codOrgTransport': self._l10n_ro_edi_stock_get_cod(transport_partner),
                    'denumireOrgTransport': transport_partner.name,
                    'dataTransport': scheduled_date,
                },
                'locStartTraseuRutier': {
                    'location_type': data['l10n_ro_edi_stock_start_loc_type'],
                },
                'locFinalTraseuRutier': {
                    'location_type': data['l10n_ro_edi_stock_end_loc_type'],
                },
                'documenteTransport': {
                    'tipDocument': "30",
                    'dataDocument': scheduled_date,
                    'numarDocument': name,
                    'observatii': data['l10n_ro_edi_stock_remarks'],
                }
            },
        }

        if data['send_type'] == 'amend':
            template_data['notificare']['uit'] = data['l10n_ro_edi_stock_document_uit']

        for loc in ('start', 'end'):
            key = 'locStartTraseuRutier' if loc == 'start' else 'locFinalTraseuRutier'

            match template_data['notificare'][key]['location_type']:
                case 'location':
                    match data['picking_type_id'].code:
                        case 'outgoing':
                            partner = data['picking_type_id'].warehouse_id.partner_id if loc == 'start' else data['partner_id']
                        case 'incoming':
                            partner = data['picking_type_id'].warehouse_id.partner_id if loc == 'end' else data['partner_id']

                    template_data['notificare'][key]['locatie'] = {
                        'codJudet': STATE_CODES[partner.state_id.code],
                        'denumireLocalitate': partner.city,
                        'denumireStrada': partner.street,
                        'codPostal': partner.zip,
                        'alteInfo': partner.street2,
                    }
                case 'bcp':
                    template_data['notificare'][key]['codPtf'] = data[f'l10n_ro_edi_stock_{loc}_bcp']
                case 'customs':
                    template_data['notificare'][key]['codBirouVamal'] = data[f'l10n_ro_edi_stock_{loc}_customs_office']

        return {'data': template_data}

    ################################################################################
    # Misc helpers
    ################################################################################

    @api.model
    def _l10n_ro_edi_stock_get_available_location_types(self, operation_type, location: Literal['start', 'end']) -> str:
        """
        :return comma separated list of available location types for the start or end location based on the operation type
        """
        if operation_type == LOCATION_TYPE_MAP[location]['customs_code']:
            return 'location,bcp,customs'
        elif operation_type in LOCATION_TYPE_MAP[location]['bcp_codes']:
            return 'location,bcp'
        else:
            return 'location'

    @api.model
    def _l10n_ro_edi_stock_get_cod(self, record):
        """
        :return the records vat in the format required by anaf
        """
        return record.vat.upper().replace('RO', '')

    @api.model
    def _l10n_ro_edi_stock_get_gross_weight(self, move):
        """
        :return the gross weight of a stock.move
        """
        return move.weight + sum(line.result_package_id.shipping_weight for line in move.move_line_ids if line.result_package_id)

    def _l10n_ro_edi_stock_report_unhandled_document_state(self, state: str):
        """
        Reports an unknown document state from anaf to the user in the chatter
        """
        self.ensure_one()
        self.message_post(body=_("Unhandled eTransport document state: %(state)s", state=state))
