import requests

from odoo.addons.l10n_ro_edi_stock.models.l10n_ro_edi_stock_document import DOCUMENT_STATES
from odoo import api, fields, models, _

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


class L10nRoEdiStockETransportInterface(models.Model):
    _name = 'l10n_ro.edi.stock.etransport.interface'
    _description = "Interface for Romanian eTransport"

    picking_id = fields.Many2one(comodel_name='stock.picking', default=None)

    l10n_ro_edi_stock_document_ids = fields.One2many(comodel_name='l10n_ro.edi.stock.document', inverse_name='interface_id')
    l10n_ro_edi_stock_document_message = fields.Char(compute='_compute_current_document_data')
    l10n_ro_edi_stock_document_load_id = fields.Char(compute='_compute_current_document_data')
    l10n_ro_edi_stock_document_uit = fields.Char(compute='_compute_current_document_data')

    l10n_ro_edi_stock_state = fields.Selection(selection=DOCUMENT_STATES, compute='_compute_current_document_data')

    l10n_ro_edi_stock_move_ids = fields.One2many(comodel_name='stock.move', compute='_compute_l10n_ro_edi_stock_move_ids', recursive=True)
    l10n_ro_edi_stock_company_id = fields.Many2one(comodel_name='res.company', compute='_compute_l10n_ro_edi_stock_company_id', recursive=True)
    l10n_ro_edi_stock_carrier_id = fields.Many2one(comodel_name='delivery.carrier', compute='_compute_l10n_ro_edi_stock_carrier_id', recursive=True)

    l10n_ro_edi_stock_operation_type = fields.Selection(selection=OPERATION_TYPES, string="Operation Type")
    l10n_ro_edi_stock_available_operation_scopes = fields.Char(compute='_compute_l10n_ro_edi_stock_available_operation_scopes')
    l10n_ro_edi_stock_operation_scope = fields.Selection(selection=OPERATION_SCOPES, string="Operation Scope")

    l10n_ro_edi_stock_vehicle_number = fields.Char(string="Vehicle Number", size=20)
    l10n_ro_edi_stock_trailer_1_number = fields.Char(string="Trailer 1 Number", size=20)
    l10n_ro_edi_stock_trailer_2_number = fields.Char(string="Trailer 2 Number", size=20)

    l10n_ro_edi_stock_available_start_loc_types = fields.Char(compute='_compute_available_location_types')
    l10n_ro_edi_stock_start_loc_type = fields.Selection(selection=LOCATION_TYPES, string="Location Type", default='location')

    l10n_ro_edi_stock_available_end_loc_types = fields.Char(compute='_compute_available_location_types')
    l10n_ro_edi_stock_end_loc_type = fields.Selection(selection=LOCATION_TYPES, string="Location Type", default='location')

    # Data fields for every location type
    l10n_ro_edi_stock_start_bcp = fields.Selection(selection=BORDER_CROSSING_POINTS, string="Border Crossing Point")
    l10n_ro_edi_stock_start_customs_office = fields.Selection(selection=CUSTOMS_OFFICES, string="Custom Office")
    l10n_ro_edi_stock_start_state_id = fields.Many2one(comodel_name='res.country.state', string="State", domain="[('country_id.code', '=', 'RO')]")
    l10n_ro_edi_stock_start_city = fields.Char(string="City")
    l10n_ro_edi_stock_start_street = fields.Char(string="Street")
    l10n_ro_edi_stock_start_zip = fields.Char(string="Postal Code")
    l10n_ro_edi_stock_start_other_info = fields.Char(string="Other Info")

    l10n_ro_edi_stock_end_bcp = fields.Selection(selection=BORDER_CROSSING_POINTS, string="Border Crossing Point")
    l10n_ro_edi_stock_end_customs_office = fields.Selection(selection=CUSTOMS_OFFICES, string="Customs Office")
    l10n_ro_edi_stock_end_state_id = fields.Many2one(comodel_name='res.country.state', string="State", domain="[('country_id.code', '=', 'RO')]")
    l10n_ro_edi_stock_end_city = fields.Char(string="City")
    l10n_ro_edi_stock_end_street = fields.Char(string="Street")
    l10n_ro_edi_stock_end_zip = fields.Char(string="Postal Code")
    l10n_ro_edi_stock_end_other_info = fields.Char(string="Other Info")

    l10n_ro_edi_stock_remarks = fields.Text(string="Remarks")

    ################################################################################
    # Compute Methods
    ################################################################################

    @api.depends('picking_id.move_ids')
    def _compute_l10n_ro_edi_stock_move_ids(self):
        for interface in self:
            interface.l10n_ro_edi_stock_move_ids = interface.picking_id.move_ids

    @api.depends('picking_id.company_id')
    def _compute_l10n_ro_edi_stock_company_id(self):
        for interface in self:
            interface.l10n_ro_edi_stock_company_id = interface.picking_id.company_id

    @api.depends('picking_id.carrier_id')
    def _compute_l10n_ro_edi_stock_carrier_id(self):
        for interface in self:
            interface.l10n_ro_edi_stock_carrier_id = interface.picking_id.carrier_id

    @api.depends('l10n_ro_edi_stock_operation_type')
    def _compute_l10n_ro_edi_stock_available_operation_scopes(self):
        for interface in self:
            allowed_scopes = [c for c, dummy in OPERATION_SCOPES]

            if interface.l10n_ro_edi_stock_operation_type:
                allowed_scopes = OPERATION_TYPE_TO_ALLOWED_SCOPE_CODES.get(interface.l10n_ro_edi_stock_operation_type, ("9999",))

                if interface.l10n_ro_edi_stock_operation_scope not in allowed_scopes:
                    interface.l10n_ro_edi_stock_operation_scope = None
            elif interface.l10n_ro_edi_stock_operation_scope:
                interface.l10n_ro_edi_stock_operation_scope = None

            interface.l10n_ro_edi_stock_available_operation_scopes = ','.join(allowed_scopes)

    @api.depends('l10n_ro_edi_stock_operation_type')
    def _compute_available_location_types(self):
        for interface in self:
            interface.l10n_ro_edi_stock_available_start_loc_types = interface._get_available_location_types('start')
            interface.l10n_ro_edi_stock_available_end_loc_types = interface._get_available_location_types('end')

    @api.depends('l10n_ro_edi_stock_document_ids')
    def _compute_current_document_data(self):
        for interface in self:
            document = interface._get_current_document()

            interface.l10n_ro_edi_stock_state = document.state if document else False
            interface.l10n_ro_edi_stock_document_message = document.message if document else False
            interface.l10n_ro_edi_stock_document_load_id = document.load_id if document else False
            interface.l10n_ro_edi_stock_document_uit = document.uit if document else False

    ################################################################################
    # Reset Data Methods
    ################################################################################

    def _reset_location_type(self):
        for interface in self:
            interface.l10n_ro_edi_stock_start_loc_type = 'location'
            interface.l10n_ro_edi_stock_end_loc_type = 'location'

    def _reset_location_data(self, location: str):
        for interface in self:
            setattr(interface, f'l10n_ro_edi_stock_{location}_bcp', None)
            setattr(interface, f'l10n_ro_edi_stock_{location}_customs_office', None)
            setattr(interface, f'l10n_ro_edi_stock_{location}_state_id', None)
            setattr(interface, f'l10n_ro_edi_stock_{location}_zip', None)
            setattr(interface, f'l10n_ro_edi_stock_{location}_city', None)
            setattr(interface, f'l10n_ro_edi_stock_{location}_street', None)
            setattr(interface, f'l10n_ro_edi_stock_{location}_other_info', None)

    def _get_available_location_types(self, location: str) -> str:
        """
        :param location: 'start' | 'end'
        :return comma separated list of available location types
        """
        if self.l10n_ro_edi_stock_operation_type == LOCATION_TYPE_MAP[location]['customs_code']:
            return 'location,bcp,customs'
        elif self.l10n_ro_edi_stock_operation_type in LOCATION_TYPE_MAP[location]['bcp_codes']:
            return 'location,bcp'
        else:
            return 'location'

    def _validate_data(self):
        self.ensure_one()
        errors = []

        # operation type
        if not self.l10n_ro_edi_stock_operation_type:
            errors.append(_("Operation type is missing."))
            return errors  # return prematurely because a lot of fields depend on the operation type

        # operation scope
        if not self.l10n_ro_edi_stock_operation_scope:
            errors.append(_("Operation scope is missing."))

        # vehicle & trailer numbers
        if not self.l10n_ro_edi_stock_vehicle_number:
            errors.append(_("Vehicle number is missing."))

        # All filled-in vehicle and trailer numbers must be unique
        license_plates = [num for num in (self.l10n_ro_edi_stock_vehicle_number, self.l10n_ro_edi_stock_trailer_1_number, self.l10n_ro_edi_stock_trailer_2_number) if num]
        if len(license_plates) != len(set(license_plates)):
            errors.append(_("Vehicle number and trailer number fields must be unique."))

        # rate codes
        if self.l10n_ro_edi_stock_operation_type not in ('60', '70'):
            product_without_code_names = {move_line.product_id.name
                                          for move in self.l10n_ro_edi_stock_move_ids
                                          for move_line in move.move_line_ids
                                          if not move_line.product_id.intrastat_code_id.code}

            if product_without_code_names:
                if len(product_without_code_names) == 1:
                    (product_name,) = product_without_code_names
                    errors.append(_("Product %(name)s is missing the intrastat code value.", name=product_name))
                else:
                    errors.append(_("Products %(names)s are missing the intrastat code value.", names=", ".join(product_without_code_names)))

        # Location types
        if not self.l10n_ro_edi_stock_start_loc_type:
            errors.append(_("'Start Location Type' is missing"))
            return errors  # return prematurely because all the start location fields depend on this field

        if not self.l10n_ro_edi_stock_end_loc_type:
            errors.append(_("'End Location Type' is missing"))
            return errors  # return prematurely because all the end location fields depend on this field

        # Location fields
        for location in ('start', 'end'):
            loc_value = getattr(self, f'l10n_ro_edi_stock_{location}_loc_type')
            loc_group = _("'Start Location'") if location == 'start' else _("'End Location'")

            if loc_value == 'bcp' and not getattr(self, f'l10n_ro_edi_stock_{location}_bcp'):
                errors.append(_("The border crossing point is missing under %(location_group)s", location_group=loc_group))
            elif loc_value == 'customs' and not getattr(self, f'l10n_ro_edi_stock_{location}_customs_office'):
                errors.append(_("The customs office is missing under %(location_group)s", location_group=loc_group))
            elif loc_value == 'location':
                missing_field_names = []
                if not getattr(self, f'l10n_ro_edi_stock_{location}_state_id'):
                    missing_field_names.append(_("State"))
                if not getattr(self, f'l10n_ro_edi_stock_{location}_city'):
                    missing_field_names.append(_("City"))
                if not getattr(self, f'l10n_ro_edi_stock_{location}_street'):
                    missing_field_names.append(_("Street"))
                if not getattr(self, f'l10n_ro_edi_stock_{location}_zip'):
                    missing_field_names.append(_("Postal Code"))

                if len(missing_field_names) == 1:
                    errors.append(_("%(location_group)s is missing the %(field_name)s field.", location_group=loc_group, field_name=missing_field_names[0]))
                elif len(missing_field_names) > 1:
                    errors.append(_("%(location_group)s is missing following fields: %(field_names)s", location_group=loc_group, field_names=missing_field_names))

        # carrier partner fields
        if self.l10n_ro_edi_stock_carrier_id.l10n_ro_edi_stock_partner_id.country_id.code != 'RO':
            errors.append(_("The delivery carrier partner has to be located in Romania."))
        else:
            missing_carrier_partner_fields = []
            partner = self.l10n_ro_edi_stock_carrier_id.l10n_ro_edi_stock_partner_id

            if not partner.city:
                missing_carrier_partner_fields.append(_("City"))

            if not partner.street:
                missing_carrier_partner_fields.append(_("Street"))

            if len(missing_carrier_partner_fields) == 1:
                errors.append(_("The delivery carrier partner is missing the %(field_name)s field.", field_name=missing_carrier_partner_fields[0]))
            elif len(missing_carrier_partner_fields) > 1:
                errors.append(_("The delivery carrier partner is missing following fields: %(field_names)s", field_names=', '.join(missing_carrier_partner_fields)))

        if not self.l10n_ro_edi_stock_company_id.l10n_ro_edi_access_token:
            errors.append(_('Romanian access token not found. Please generate or fill it in the settings.'))

        return errors

    def _check_fetch_values(self, errors=None) -> list:
        if errors is None:
            errors = []
        self.ensure_one()

        if not self.l10n_ro_edi_stock_company_id.l10n_ro_edi_access_token:
            errors.append(_('Romanian access token not found. Please generate or fill it in the settings.'))
            return errors

        match self.l10n_ro_edi_stock_state:
            case 'etransport_sending_failed':
                if self._get_last_etransport_sent_document():
                    errors.append(_("This document has not been successfully sent yet because it contains errors."))
                else:
                    errors.append(_("This document has not been corrected yet because it contains errors."))
            case 'etransport_sent':
                errors.append(_("This document has already been successfully sent to anaf."))

        return errors

    ################################################################################
    # Template Helpers
    ################################################################################

    def _get_declarant_ref(self) -> str:
        self.ensure_one()
        return self.picking_id.name

    def _get_scheduled_date(self):
        self.ensure_one()
        return self.picking_id.scheduled_date.date()

    def _get_commercial_partner(self):
        self.ensure_one()
        return self.picking_id.partner_id.commercial_partner_id

    def _get_transport_partner(self):
        self.ensure_one()
        return self.picking_id.carrier_id.l10n_ro_edi_stock_partner_id

    ################################################################################
    # Document Helpers
    ################################################################################

    def _create_document_etransport_sending(self, values: dict[str, object]):
        """
        Expected keys in the values dict (see fields of l10n_ro.edi.stock.document model):
            - 'load_id' (required)
            - 'uit' (required)
        Forbidden keys:
            - 'interface_id'
            - 'state'
        """
        self.ensure_one()
        return self.env['l10n_ro.edi.stock.document'].create({
            'interface_id': self.id,
            'state': 'etransport_sending',
            **values,
        })

    def _create_document_etransport_sending_failed(self, values: dict[str, object]):
        """
        Expected keys in the values dict (see fields of l10n_ro.edi.stock.document model):
            - 'message' (required)
            - 'load_id' (optional) defaults to None
            - 'uit' (optional) defaults to None
        Forbidden keys:
            - 'interface_id'
            - 'state'
        """
        self.ensure_one()

        values.setdefault('load_id', None)
        values.setdefault('uit', None)

        return self.env['l10n_ro.edi.stock.document'].create({
            'interface_id': self.id,
            'state': 'etransport_sending_failed',
            **values,
        })

    def _create_document_etransport_sent(self, values: dict[str, object]):
        """
        Expected keys in the values dict (see fields of l10n_ro.edi.stock.document model):
            - 'load_id' (required)
            - 'uit' (required)
        Forbidden keys:
            - 'interface_id'
            - 'state'
        """
        self.ensure_one()
        return self.env['l10n_ro.edi.stock.document'].create({
            'interface_id': self.id,
            'state': 'etransport_sent',
            **values,
        })

    def _get_failed_documents(self):
        self.ensure_one()
        return self.l10n_ro_edi_stock_document_ids.filtered(lambda doc: doc.state == 'etransport_sending_failed')

    def _get_etransport_sending_and_failed_documents(self):
        self.ensure_one()
        return self.l10n_ro_edi_stock_document_ids.filtered(lambda doc: doc.state in ('etransport_sending_failed', 'etransport_sending'))

    def _get_last_etransport_sent_document(self):
        self.ensure_one()
        sent_documents = self.l10n_ro_edi_stock_document_ids.filtered(lambda doc: doc.state == 'etransport_sent').sorted()

        if sent_documents:
            return sent_documents[0]

    def _get_current_document(self):
        self.ensure_one()
        return self.l10n_ro_edi_stock_document_ids.sorted()[0] if self.l10n_ro_edi_stock_document_ids else None

    ################################################################################
    # Send Logic
    ################################################################################

    def _send_etransport_document(self, send_type: str):
        """
        Send the eTransport document to anaf
        :param send_type: 'send' (initial sending of document) | 'amend' (correct the already sent document)
        """
        self.ensure_one()

        if errors := self._validate_data():
            self._get_failed_documents().unlink()
            document_values = {'message': '\n'.join(errors)}

            if send_type == 'amend':
                last_sent_document = self._get_last_etransport_sent_document()
                document_values |= {'load_id': last_sent_document.load_id, 'uit': last_sent_document.uit}

            self._create_document_etransport_sending_failed(document_values)
            return

        commercial_partner = self._get_commercial_partner()
        commercial_partner_code = None

        if commercial_partner.vat:
            commercial_partner_code = self._get_cod(commercial_partner)
        elif self.l10n_ro_edi_stock_operation_type == '30':
            commercial_partner_code = 'PF'

        result = self.env['l10n_ro.edi.stock.document']._send_etransport_document(company=self.l10n_ro_edi_stock_company_id, template_data={
            'send_type': send_type,
            'interface': self,
            'STATE_CODES': STATE_CODES,
            'declarant_ref': self._get_declarant_ref(),
            'partner': commercial_partner,
            'partner_cod': commercial_partner_code,
            'transport_partner': self._get_transport_partner(),
            'scheduled_date': self._get_scheduled_date(),
            'vehicle_number': self.l10n_ro_edi_stock_vehicle_number.upper(),
            'trailer1': (self.l10n_ro_edi_stock_trailer_1_number or '').upper() or None,
            'trailer2': (self.l10n_ro_edi_stock_trailer_2_number or '').upper() or None,
            'get_gross_weight': self._get_gross_weight,
            'get_cod': self._get_cod,
        })

        if 'error' in result:
            self._get_failed_documents().unlink()
            document_values = {'message': result['error']}

            if send_type == 'amend':
                last_sent_document = self._get_last_etransport_sent_document()
                document_values |= {'load_id': last_sent_document.load_id, 'uit': last_sent_document.uit}

            self._create_document_etransport_sending_failed(document_values)
        else:
            self._get_etransport_sending_and_failed_documents().unlink()

            content = result['content']
            uit = content['UIT'] if send_type == 'send' else self._get_last_etransport_sent_document().uit
            self._create_document_etransport_sending({'load_id': content['index_incarcare'], 'uit': uit})

    def _fetch_document_status(self):
        session = requests.Session()
        documents_to_delete = self.env['l10n_ro.edi.stock.document']
        to_fetch = self.filtered(lambda inter: inter.l10n_ro_edi_stock_state == 'etransport_sending')

        for interface in to_fetch:
            current_sending_document = interface.l10n_ro_edi_stock_document_ids.filtered(lambda doc: doc.state == 'etransport_sending')[0]

            if errors := interface._check_fetch_values():
                documents_to_delete |= interface._get_failed_documents()
                interface._create_document_etransport_sending_failed({'message': '\n'.join(errors), 'load_id': current_sending_document.load_id, 'uit': current_sending_document.uit})
                continue

            result = self.env['l10n_ro.edi.stock.document']._fetch_etransport_document(
                company=interface.l10n_ro_edi_stock_company_id,
                load_id=current_sending_document.load_id,
                session=session,
            )

            if 'error' in result:
                documents_to_delete |= interface._get_failed_documents()
                interface._create_document_etransport_sending_failed({'message': result['error'], 'load_id': current_sending_document.load_id, 'uit': current_sending_document.uit})
            else:
                documents_to_delete |= interface._get_etransport_sending_and_failed_documents()
                match state := result['content']['stare']:
                    case 'ok':
                        interface._create_document_etransport_sent({'load_id': current_sending_document.load_id, 'uit': current_sending_document.uit})
                    case 'in prelucrare':
                        # Document is still being sent
                        interface._create_document_etransport_sending({'load_id': current_sending_document.load_id, 'uit': current_sending_document.uit})
                    case 'XML cu erori nepreluat de sistem':
                        interface._create_document_etransport_sending_failed({'message': _("XML contains errors."), 'load_id': current_sending_document.load_id, 'uit': current_sending_document.uit})
                    case _:
                        interface._report_unhandled_document_state(state)

        documents_to_delete.unlink()

    @api.model
    def _get_gross_weight(self, move):
        return move.weight + sum(line.result_package_id.shipping_weight for line in move.move_line_ids if line.result_package_id)

    @api.model
    def _get_cod(self, record):
        return record.vat.upper().replace('RO', '')

    def _report_unhandled_document_state(self, state: str):
        self.ensure_one()
        self.picking_id.message_post(body=_("Unhandled eTransport document state: %(state)s", state=state))
