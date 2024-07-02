import markupsafe
import requests
import re

from odoo import api, fields, models, _

DOCUMENT_STATES = [
    ('draft', "Draft"),
    ('sending', "Sending"),
    ('sending_failed', "Error"),
    ('amending', "Sending"),
    ('amending_failed', "Error"),
    ('sent', 'Sent'),
]

SCHEMATRON_ERROR_ID_PATTERN = r'BR-(?:CL-)?\d{3}'

ETRANSPORT_TEST_URL = 'https://api.anaf.ro/test/ETRANSPORT/ws/v1'
ETRANSPORT_PROD_URL = 'https://api.anaf.ro/prod/ETRANSPORT/ws/v1'

OPERATION_TYPE_TO_ALLOWED_SCOPE_CODES = {
    "10": ("101", "201", "301", "401", "501", "601", "703", "801", "802", "901", "1001", "1101", "9901"),
    "20": ("101", "301", "703", "801", "802", "9901"),
    "30": ("101", "704", "705", "9901"),
}

LOCATION_TYPE_MAP = {
    'start': {
        'customs_code': '40',
        'bcp_codes': ('10', '12', '14', '60'),
    },
    'end': {
        'customs_code': '50',
        'bcp_codes': ('10', '20', '22', '24', '70')
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

SELECTION_LOC_TYPE_1 = [('location', "Location"), ('bcp', "Border Crossing Point")]
SELECTION_LOC_TYPE_2 = [('location', "Location"), ('bcp', "Border Crossing Point"), ('customs', "Customs Office")]


class L10nRoEdiETransportDocument(models.Model):
    _name = 'l10n_ro.edi.etransport.document'
    _description = "Romanian eTransport document"
    _order = 'create_date DESC, id DESC'

    picking_id = fields.Many2one(comodel_name='stock.picking', default=None)
    l10n_ro_edi_etransport_move_ids = fields.One2many(comodel_name='stock.move', compute='_compute_l10n_ro_edi_etransport_move_ids', recursive=True)
    l10n_ro_edi_etransport_company_id = fields.Many2one(comodel_name='res.company', compute='_compute_l10n_ro_edi_etransport_company_id', recursive=True)
    l10n_ro_edi_etransport_carrier_id = fields.Many2one(comodel_name='delivery.carrier', compute='_compute_l10n_ro_edi_etransport_carrier_id', recursive=True)

    l10n_ro_edi_etransport_operation_type_id = fields.Many2one(comodel_name='l10n_ro.edi.etransport.operation.type', string="Operation Type")
    l10n_ro_edi_etransport_operation_type_code = fields.Char(related='l10n_ro_edi_etransport_operation_type_id.code')

    l10n_ro_edi_etransport_operation_allowed_scope_ids = fields.Many2many(comodel_name='l10n_ro.edi.etransport.operation.scope', compute='_compute_scope_ids')
    l10n_ro_edi_etransport_operation_scope_id = fields.Many2one(comodel_name='l10n_ro.edi.etransport.operation.scope',
                                                                string="Operation Scope",
                                                                domain="[('id', 'in', l10n_ro_edi_etransport_operation_allowed_scope_ids)]")

    l10n_ro_edi_etransport_vehicle_number = fields.Char(string="Vehicle Number", size=20)
    l10n_ro_edi_etransport_trailer_1_number = fields.Char(string="Trailer 1 Number", size=20)
    l10n_ro_edi_etransport_trailer_2_number = fields.Char(string="Trailer 2 Number", size=20)

    l10n_ro_edi_etransport_start_loc_type_1 = fields.Selection(selection=SELECTION_LOC_TYPE_1, string="Location Type", default='location')
    l10n_ro_edi_etransport_start_loc_type_2 = fields.Selection(selection=SELECTION_LOC_TYPE_2, string="Location Type", default='location')

    l10n_ro_edi_etransport_end_loc_type_1 = fields.Selection(selection=SELECTION_LOC_TYPE_1, string="Location Type", default='location')
    l10n_ro_edi_etransport_end_loc_type_2 = fields.Selection(selection=SELECTION_LOC_TYPE_2, string="Location Type", default='location')

    l10n_ro_edi_etransport_start_loc_value = fields.Char(compute='_compute_start_loc_value')
    l10n_ro_edi_etransport_end_loc_value = fields.Char(compute='_compute_end_loc_value')

    l10n_ro_edi_etransport_start_loc_type_index = fields.Integer(compute='_compute_start_loc_type_index')
    l10n_ro_edi_etransport_end_loc_type_index = fields.Integer(compute='_compute_end_loc_type_index')

    # Data fields for every location type
    l10n_ro_edi_etransport_start_bcp = fields.Selection(selection=BORDER_CROSSING_POINTS, string="Border Crossing Point")
    l10n_ro_edi_etransport_start_customs_office = fields.Many2one(comodel_name='l10n_ro.edi.etransport.customs', string="Customs Office")
    l10n_ro_edi_etransport_start_state_id = fields.Many2one(comodel_name='res.country.state', string="State", domain="[('country_id.code', '=', 'RO')]")
    l10n_ro_edi_etransport_start_city = fields.Char(string="City")
    l10n_ro_edi_etransport_start_street = fields.Char(string="Street")
    l10n_ro_edi_etransport_start_zip = fields.Char(string="Postal Code")
    l10n_ro_edi_etransport_start_other_info = fields.Char(string="Other Info")

    l10n_ro_edi_etransport_end_bcp = fields.Selection(selection=BORDER_CROSSING_POINTS, string="Border Crossing Point")
    l10n_ro_edi_etransport_end_customs_office = fields.Many2one(comodel_name='l10n_ro.edi.etransport.customs', string="Customs Office")
    l10n_ro_edi_etransport_end_state_id = fields.Many2one(comodel_name='res.country.state', string="State", domain="[('country_id.code', '=', 'RO')]")
    l10n_ro_edi_etransport_end_city = fields.Char(string="City")
    l10n_ro_edi_etransport_end_street = fields.Char(string="Street")
    l10n_ro_edi_etransport_end_zip = fields.Char(string="Postal Code")
    l10n_ro_edi_etransport_end_other_info = fields.Char(string="Other Info")

    l10n_ro_edi_etransport_remarks = fields.Text(string="Remarks")

    l10n_ro_edi_etransport_state = fields.Selection(selection=DOCUMENT_STATES, string="eTransport Status", default='draft', copy=False)
    l10n_ro_edi_etransport_message = fields.Char(string="Message", copy=False)
    l10n_ro_edi_etransport_uit = fields.Char(help="UIT of this eTransport document.", copy=False)
    l10n_ro_edi_etransport_load_id = fields.Char(help="Id of this document used for interacting with the anaf api.", copy=False)

    def _reset_location_type(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_start_loc_type_1 = 'location'
            doc.l10n_ro_edi_etransport_start_loc_type_2 = 'location'
            doc.l10n_ro_edi_etransport_end_loc_type_1 = 'location'
            doc.l10n_ro_edi_etransport_end_loc_type_2 = 'location'

    def _reset_location_data(self, location: str):
        for doc in self:
            setattr(doc, f'l10n_ro_edi_etransport_{location}_bcp', None)
            setattr(doc, f'l10n_ro_edi_etransport_{location}_customs_office', None)
            setattr(doc, f'l10n_ro_edi_etransport_{location}_state_id', None)
            setattr(doc, f'l10n_ro_edi_etransport_{location}_zip', None)
            setattr(doc, f'l10n_ro_edi_etransport_{location}_city', None)
            setattr(doc, f'l10n_ro_edi_etransport_{location}_street', None)
            setattr(doc, f'l10n_ro_edi_etransport_{location}_other_info', None)

    @api.depends('l10n_ro_edi_etransport_operation_type_id')
    def _compute_scope_ids(self):
        for doc in self:
            scope_domain = []

            if doc.l10n_ro_edi_etransport_operation_type_id:
                allowed_scope_codes = OPERATION_TYPE_TO_ALLOWED_SCOPE_CODES.get(doc.l10n_ro_edi_etransport_operation_type_id.code, ("9999",))
                scope_domain = [('code', 'in', allowed_scope_codes)]

                if doc.l10n_ro_edi_etransport_operation_scope_id and doc.l10n_ro_edi_etransport_operation_scope_id.code not in allowed_scope_codes:
                    doc.l10n_ro_edi_etransport_operation_scope_id = None
            elif doc.l10n_ro_edi_etransport_operation_scope_id:
                doc.l10n_ro_edi_etransport_operation_scope_id = None

            doc.l10n_ro_edi_etransport_operation_allowed_scope_ids = doc.env['l10n_ro.edi.etransport.operation.scope'].search(scope_domain)

    @api.depends('picking_id.move_ids')
    def _compute_l10n_ro_edi_etransport_move_ids(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_move_ids = doc.picking_id.move_ids

    @api.depends('picking_id.company_id')
    def _compute_l10n_ro_edi_etransport_company_id(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_company_id = doc.picking_id.company_id

    @api.depends('picking_id.carrier_id')
    def _compute_l10n_ro_edi_etransport_carrier_id(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_carrier_id = doc.picking_id.carrier_id

    @api.depends('l10n_ro_edi_etransport_operation_type_id', 'l10n_ro_edi_etransport_start_loc_type_1', 'l10n_ro_edi_etransport_start_loc_type_2')
    def _compute_start_loc_value(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_start_loc_value = doc._get_chosen_location_type('start')

    @api.depends('l10n_ro_edi_etransport_operation_type_id', 'l10n_ro_edi_etransport_end_loc_type_1', 'l10n_ro_edi_etransport_end_loc_type_2')
    def _compute_end_loc_value(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_end_loc_value = doc._get_chosen_location_type('end')

    @api.depends('l10n_ro_edi_etransport_operation_type_code')
    def _compute_start_loc_type_index(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_start_loc_type_index = doc._get_location_type_field_index('start')

    @api.depends('l10n_ro_edi_etransport_operation_type_code')
    def _compute_end_loc_type_index(self):
        for doc in self:
            doc.l10n_ro_edi_etransport_end_loc_type_index = doc._get_location_type_field_index('end')

    def _check_values(self):
        self.ensure_one()
        errors = []

        # operation type
        if not self.l10n_ro_edi_etransport_operation_type_id:
            errors.append(_("Operation type is missing."))
            return errors  # return prematurely because a lot of fields depend on the operation type

        # operation scope
        if not self.l10n_ro_edi_etransport_operation_scope_id:
            errors.append(_("Operation scope is missing."))

        # vehicle & trailer numbers
        if not self.l10n_ro_edi_etransport_vehicle_number:
            errors.append(_("Vehicle number is missing."))

        # All filled-in vehicle and trailer numbers must be unique
        license_plates = [num for num in (self.l10n_ro_edi_etransport_vehicle_number, self.l10n_ro_edi_etransport_trailer_1_number, self.l10n_ro_edi_etransport_trailer_2_number) if num]
        if len(license_plates) != len(set(license_plates)):
            errors.append(_("Vehicle number and trailer number fields must be unique."))

        # rate codes
        if self.l10n_ro_edi_etransport_operation_type_code not in ('60', '70'):
            products_without_code = [move_line.product_id for move in self.l10n_ro_edi_etransport_move_ids
                                     for move_line in move.move_line_ids
                                     if not move_line.product_id.intrastat_code_id.code]

            if products_without_code:
                if len(products_without_code) == 1:
                    errors.append(_("Product %(name)s is missing the intrastat code value.", name=products_without_code[0].name))
                else:
                    names = ", ".join(product.name for product in products_without_code)
                    errors.append(_("Products %(names)s are missing the intrastat code value.", names=names))

        # Location types
        def check_location_type(location: str) -> str | None:
            loc_type_idx = getattr(self, f'l10n_ro_edi_etransport_{location}_loc_type_index')
            if loc_type_idx not in (1, 2):
                return

            if not getattr(self, f'l10n_ro_edi_etransport_{location}_loc_type_{loc_type_idx}'):
                match location:
                    case 'start':
                        return _("'Start Location Type' is missing")
                    case 'end':
                        return _("'End Location Type' is missing")

        for loc in ('start', 'end'):
            if loc_error := check_location_type(loc):
                errors.append(loc_error)
                return errors  # return prematurely because all the location fields depend on these fields

        # location fields
        def check_location_fields(location: str):
            loc_value = getattr(self, f'l10n_ro_edi_etransport_{location}_loc_value')
            loc_group = _("'Start Location'") if location == 'start' else _("'End Location'")

            if loc_value == 'bcp' and not getattr(self, f'l10n_ro_edi_etransport_{location}_bcp'):
                errors.append(_("The border crossing point is missing under %(location_group)s", location_group=loc_group))
            elif loc_value == 'customs' and not getattr(self, f'l10n_ro_edi_etransport_{location}_customs_office'):
                errors.append(_("The customs office is missing under %(location_group)s", location_group=loc_group))
            elif loc_value == 'location':
                missing_field_names = []
                if not getattr(self, f'l10n_ro_edi_etransport_{location}_state_id'):
                    missing_field_names.append(_("State"))
                if not getattr(self, f'l10n_ro_edi_etransport_{location}_city'):
                    missing_field_names.append(_("City"))
                if not getattr(self, f'l10n_ro_edi_etransport_{location}_street'):
                    missing_field_names.append(_("Street"))
                if not getattr(self, f'l10n_ro_edi_etransport_{location}_zip'):
                    missing_field_names.append(_("Postal Code"))

                if len(missing_field_names) == 1:
                    errors.append(_("%(location_group)s is missing the %(field_name)s field.", location_group=loc_group, field_name=missing_field_names[0]))
                elif len(missing_field_names) > 1:
                    errors.append(_("%(location_group)s is missing following fields: %(field_names)s", location_group=loc_group, field_names=missing_field_names))

        check_location_fields('start')
        check_location_fields('end')

        # carrier partner fields
        if self.l10n_ro_edi_etransport_carrier_id.l10n_ro_edi_etransport_partner_id.country_id.code != 'RO':
            errors.append(_("The delivery carrier partner has to be located in Romania."))
        else:
            missing_carrier_partner_fields = []
            partner = self.l10n_ro_edi_etransport_carrier_id.l10n_ro_edi_etransport_partner_id

            if not partner.city:
                missing_carrier_partner_fields.append(_("City"))

            if not partner.street:
                missing_carrier_partner_fields.append(_("Street"))

            if len(missing_carrier_partner_fields) == 1:
                errors.append(_("The delivery carrier partner is missing the %(field_name)s field.", field_name=missing_carrier_partner_fields[0]))
            elif len(missing_carrier_partner_fields) > 1:
                errors.append(_("The delivery carrier partner is missing following fields: %(field_names)s", field_names=', '.join(missing_carrier_partner_fields)))

        errors.extend(self.l10n_ro_edi_etransport_company_id._l10n_ro_edi_get_errors_pre_request())

        return errors

    def _get_chosen_location_type(self, location: str) -> str:
        """ Calculates the location type based on the allowed location fields (which depend on the operation type) and which of these fields have been filled in.
        :param location: 'start' | 'end'
        :return the chosen location type, by default this is 'location'.
        """
        field_idx = self._get_location_type_field_index(location)
        if field_idx == -1:
            return 'location'
        else:
            return getattr(self, f'l10n_ro_edi_etransport_{location}_loc_type_{field_idx}')

    def _get_location_type_field_index(self, location: str) -> int:
        """
        :param location: 'start' | 'end'
        :return the index of the location type field (ex. for index = 2 => 'l10n_ro_edi_etransport_{location}_loc_type_2'
        """
        if self.l10n_ro_edi_etransport_operation_type_code == LOCATION_TYPE_MAP[location]['customs_code']:
            return 2
        elif self.l10n_ro_edi_etransport_operation_type_code in LOCATION_TYPE_MAP[location]['bcp_codes']:
            return 1
        else:
            # Only 'location' is possible (this possibility has no dedicated field, so we return -1)
            return -1

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
        return self.picking_id.carrier_id.l10n_ro_edi_etransport_partner_id

    def _sending_failed(self, message: str, send_type: str):
        self.ensure_one()
        self.l10n_ro_edi_etransport_message = message
        self.l10n_ro_edi_etransport_state = 'sending_failed' if send_type == 'send' else 'amending_failed'

    def _sending(self, load_id: str, uit: str, send_type: str):
        self.ensure_one()
        self.l10n_ro_edi_etransport_state = 'sending' if send_type == 'send' else 'amending'
        self.l10n_ro_edi_etransport_uit = uit
        self.l10n_ro_edi_etransport_load_id = load_id
        self.l10n_ro_edi_etransport_message = None

    def _sent(self):
        self.ensure_one()
        self.l10n_ro_edi_etransport_state = 'sent'
        self.l10n_ro_edi_etransport_message = None

    @api.model
    def _make_etransport_request(self, company, endpoint: str, method: str, data=None, session=None):
        url = f"{ETRANSPORT_TEST_URL if company.l10n_ro_edi_test_env else ETRANSPORT_PROD_URL}/{endpoint}"
        headers = {
            'Content-Type': 'application/xml',
            'Authorization': f'Bearer {company.l10n_ro_edi_access_token}',
        }

        # encode data to utf-8 because it could contain some Romanian characters that are not part of latin-1
        if data:
            data = data.encode()

        try:
            caller = session or requests
            response = caller.request(method=method, url=url, data=data, headers=headers, timeout=10)
        except requests.HTTPError as e:
            return {'error': str(e)}

        match response.status_code:
            case 404:
                return {'error': response.json()['message']}
            case 403:
                return {'error': _("Access token is forbidden.")}
            case 204:
                return {'error': _("You reached the limit of requests. Please try again later.")}
            case _:
                try:
                    response.raise_for_status()
                except requests.HTTPError as e:
                    # For all other possible status_codes, just return the HTTPError
                    return {'error': str(e)}

                response_data = response.json()

                if response_data['ExecutionStatus'] == 1:
                    errors = self._cleanup_errors([error['errorMessage'] for error in response_data['Errors']])
                    return {'error': '\n'.join(errors)}

                return {'content': response_data}

    @api.model
    def _cleanup_errors(self, errors: list[str]):
        def _cleanup_schematron_error(error: str) -> str:
            for part in error.split('; '):
                key, value = part.split('=', maxsplit=1)
                if key == 'textEroare':
                    return value.strip()

        return [_cleanup_schematron_error(err) if re.search(SCHEMATRON_ERROR_ID_PATTERN, err) else err.strip() for err in errors]

    def _send_etransport(self, send_type: str = 'send'):
        """
        Send the eTransport document to anaf
        :param send_type: 'send' (initial sending of document) | 'amend' (correct the already sent document)
        """
        self.ensure_one()

        if errors := self._check_values():
            self._sending_failed(message='\n'.join(errors), send_type=send_type)
            return

        template = self.env['ir.ui.view']._render_template('l10n_ro_edi_etransport.l10n_ro_template_etransport', values={
            'send_type': send_type,
            'document': self,
            'STATE_CODES': STATE_CODES,
            'declarant_ref': self._get_declarant_ref(),
            'partner': self._get_commercial_partner(),
            'transport_partner': self._get_transport_partner(),
            'scheduled_date': self._get_scheduled_date(),
            'vehicle_number': self.l10n_ro_edi_etransport_vehicle_number.upper(),
            'trailer1': (self.l10n_ro_edi_etransport_trailer_1_number or '').upper() or None,
            'trailer2': (self.l10n_ro_edi_etransport_trailer_2_number or '').upper() or None,
        })

        cif = self.l10n_ro_edi_etransport_company_id.vat.replace('RO', '')

        result = self.env['l10n_ro.edi.etransport.document']._make_etransport_request(
            company=self.l10n_ro_edi_etransport_company_id,
            endpoint=f'upload/ETRANSP/{cif}/2',
            method='post',
            data=markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>\n") + template
        )

        if 'error' in result:
            self._sending_failed(message=result['error'], send_type=send_type)
        else:
            content = result['content']
            uit = content['UIT'] if send_type == 'send' else self.l10n_ro_edi_etransport_uit
            self._sending(load_id=content['index_incarcare'], uit=uit, send_type=send_type)

    def _status_request(self):
        if not (documents := self.filtered(lambda doc: doc.l10n_ro_edi_etransport_state in ('sending', 'amending'))):
            return

        session = requests.sessions.Session()

        for document in documents:
            send_type = 'send' if document.l10n_ro_edi_etransport_state == 'sending' else 'amend'
            if errors := document.l10n_ro_edi_etransport_company_id._l10n_ro_edi_get_errors_pre_request() or document._check_fetch_values():
                document._sending_failed(message='\n'.join(errors), send_type=send_type)
                continue

            result = self.env['l10n_ro.edi.etransport.document']._make_etransport_request(
                company=document.l10n_ro_edi_etransport_company_id,
                endpoint=f'stareMesaj/{document.l10n_ro_edi_etransport_load_id}',
                method='get',
                session=session,
            )

            if 'error' in result:
                document._sending_failed(message=result['error'], send_type=send_type)
            else:
                match state := result['content']['stare']:
                    case 'ok':
                        document._sent()
                    case 'in prelucrare':
                        # Document is still being sent so no need to update the document state
                        pass
                    case 'XML cu erori nepreluat de sistem':
                        document._sending_failed(message=_("XML contains errors."), send_type=send_type)
                    case _:
                        document._report_unhandled_document_state(state)

    def _check_fetch_values(self, errors=None) -> list:
        if errors is None:
            errors = []
        self.ensure_one()

        match self.l10n_ro_edi_etransport_state:
            case 'sending_failed':
                errors.append(_("This document has not been successfully sent yet because it contains errors."))
            case 'amending_failed':
                errors.append(_("This document has not been corrected yet because it contains errors."))
            case 'sent':
                errors.append(_("This document has already been successfully sent to anaf."))
            case 'sending', 'amending':
                if not self.l10n_ro_edi_etransport_load_id:
                    errors.append(_("This document does not have a load id."))

        return errors

    def _report_unhandled_document_state(self, state: str):
        self.ensure_one()
        self.picking_id.message_post(body=_("Unhandled eTransport document state: %(state)s", state=state))
