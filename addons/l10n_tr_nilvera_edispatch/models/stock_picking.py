import base64
import uuid
from lxml import etree
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node

CUSTOMIZATION_ID = 'TR1.2.1'
DEFAULT_TCKN = '22222222222'
UBL_VERSION_ID = '2.1'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_tr_nilvera_dispatch_scenario = fields.Selection(
        string="Dispatch Scenario",
        selection=[('TEMELIRSALIYE', 'Temel Irsaliye'), ('HALTIPI', 'Hal Tipi')],
        compute='_compute_l10n_tr_nilvera_dispatch_scenario',
        store=True,
        readonly=False,
        tracking=True,
    )
    l10n_tr_nilvera_dispatch_type = fields.Selection(
        string="Dispatch Type",
        selection=[('SEVK', 'Sevk'), ('MATBUDAN', 'Matbudan')],
        compute='_compute_l10n_tr_nilvera_dispatch_type',
        store=True,
        readonly=False,
        tracking=True,
    )
    l10n_tr_nilvera_carrier_id = fields.Many2one(string="Carrier (TR)", comodel_name='res.partner')
    l10n_tr_nilvera_buyer_id = fields.Many2one(
        string="Buyer",
        comodel_name='res.partner'
    )
    l10n_tr_nilvera_seller_supplier_id = fields.Many2one(
        string="Seller Supplier",
        comodel_name='res.partner'
    )
    l10n_tr_nilvera_buyer_originator_id = fields.Many2one(
        string="Buyer Originator",
        comodel_name='res.partner'
    )
    l10n_tr_nilvera_delivery_printed_number = fields.Char(string="Printed Delivery Note Number")
    l10n_tr_nilvera_delivery_date = fields.Date(string="Printed Delivery Note Date")
    l10n_tr_vehicle_plate = fields.Char(string="Vehicle Plate")
    l10n_tr_nilvera_trailer_plate_ids = fields.Many2many(
        string="Trailer Plates",
        comodel_name='l10n_tr.nilvera.trailer.plate',
        relation='l10n_tr_nilvera_delivery_vehicle_rel'
    )
    l10n_tr_nilvera_driver_ids = fields.Many2many(string="Drivers", comodel_name='res.partner')
    l10n_tr_nilvera_delivery_notes = fields.Char(string="Delivery Notes")
    l10n_tr_nilvera_dispatch_state = fields.Selection(
        string="State",
        selection=[('to_send', "To Send"), ('sent', "Sent")],
        compute='_compute_l10n_tr_nilvera_dispatch_state',
        store=True,
        readonly=False,
        tracking=True,
    )
    l10n_tr_nilvera_edispatch_warnings = fields.Json(copy=False)

    @api.depends('company_id')
    def _compute_l10n_tr_nilvera_dispatch_scenario(self):
        self.filtered(
            lambda p: p.country_code == 'TR'
        ).l10n_tr_nilvera_dispatch_scenario = 'TEMELIRSALIYE'

    @api.depends('company_id')
    def _compute_l10n_tr_nilvera_dispatch_type(self):
        self.filtered(
            lambda p: p.country_code == 'TR'
        ).l10n_tr_nilvera_dispatch_type = 'SEVK'

    @api.depends('state')
    def _compute_l10n_tr_nilvera_dispatch_state(self):
        self.filtered(
            lambda p: p.state == 'done' and p.country_code == 'TR'
        ).l10n_tr_nilvera_dispatch_state = 'to_send'

    def _l10n_tr_validate_edelivery_fields(self):
        self.ensure_one()
        if self.state != 'done':
            self.l10n_tr_nilvera_edispatch_warnings = {
                'invalid_transfer_state': {
                    'message': _("Please validate the transfer first to generate the XML"),
                }
            }
            return
        if self.l10n_tr_nilvera_dispatch_scenario == 'HALTIPI':
            self.l10n_tr_nilvera_edispatch_warnings = {
                'invalid_delivery_scenario': {
                    'message': _("Dispatch Scenario as Hal Tipi is currently unsupported in the module."),
                }
            }
            return
        partners = (
            self.company_id.partner_id
            | self.partner_id
            | self.l10n_tr_nilvera_carrier_id
            | self.l10n_tr_nilvera_buyer_id
            | self.l10n_tr_nilvera_seller_supplier_id
            | self.l10n_tr_nilvera_buyer_originator_id
        )
        error_messages = {
            **partners._l10n_tr_nilvera_validate_partner_details(self.partner_id)
        }
        if self.l10n_tr_nilvera_dispatch_type == 'MATBUDAN':
            if not self.l10n_tr_nilvera_delivery_date:
                error_messages['invalid_matbu_date'] = {
                    'message': _("Printed Delivery Note Date is required."),
                }
            if not self.l10n_tr_nilvera_delivery_printed_number:
                error_messages['invalid_matbu_number'] = {
                    'message': _("Printed Delivery Note Number is required."),
                }
            elif len(self.l10n_tr_nilvera_delivery_printed_number or "") != 16:
                error_messages['invalid_matbu_number'] = {
                    'message': _("Printed Delivery Number must be 16 characters."),
                }

        invalid_country_drivers = invalid_tckn_drivers = self.env['res.partner']
        for driver in self.l10n_tr_nilvera_driver_ids:
            if not driver.country_id or driver.country_id.code != 'TR':
                invalid_country_drivers |= driver
            elif not driver.vat or (driver.vat and len(driver.vat) != 11):
                invalid_tckn_drivers |= driver
        if drivers := len(invalid_country_drivers):
            error_messages['invalid_driver_country'] = {
                'message': _(
                    "Only Drivers from Türkiye are valid. Please update the Country and enter a valid TCKN in the Tax ID."
                ),
                'action_text': _(
                    "View %s",
                    drivers == 1 and invalid_country_drivers.name or _("Drivers")
                ),
                'action': invalid_country_drivers._get_records_action(
                    name=_("Drivers")
                ),
            }
        if drivers := len(invalid_tckn_drivers):
            driver_placeholder = drivers > 1 and _("Drivers") or _("%s's", invalid_tckn_drivers.name)
            error_messages['invalid_driver_tckn'] = {
                'message': _("%s TCKN is required.", driver_placeholder),
                'action_text': _("View %s", drivers == 1 and invalid_tckn_drivers.name or _("Drivers")),
                'action': invalid_tckn_drivers._get_records_action(name=_("Drivers")),
            }
        if not self.l10n_tr_nilvera_carrier_id and not self.l10n_tr_nilvera_driver_ids:
            error_messages['required_driver_details'] = {
                'message': _("At least one Driver is required."),
            }
        if not self.l10n_tr_nilvera_carrier_id and not self.l10n_tr_vehicle_plate:
            error_messages['required_vehicle_details'] = {
                'message': _("Vehicle Plate is required."),
            }
        if (
            not self.l10n_tr_nilvera_carrier_id
            and not self.l10n_tr_nilvera_driver_ids
            and not self.l10n_tr_vehicle_plate
        ):
            error_messages['required_carrier_details'] = {
                'message': _("Carrier is required (optional when both the Driver and Vehicle Plate are present)."),
            }

        self.l10n_tr_nilvera_edispatch_warnings = error_messages or False

    def _l10n_tr_export_delivery_note(self):
        self.ensure_one()
        dispatch_uuid = str(uuid.uuid4())
        drivers = []
        for driver in self.l10n_tr_nilvera_driver_ids:
            driver_name = driver.name.split(' ', 1)
            drivers.append({
                'name': driver_name[0],
                'fname': driver_name[1] if len(driver_name) > 1 else '\u200B',
                'tckn': driver.vat
            })
        scheduled_date_local = fields.Datetime.context_timestamp(
            self.with_context(tz='Europe/Istanbul'),
            self.scheduled_date
        )
        date_done_local = fields.Datetime.context_timestamp(
            self.with_context(tz='Europe/Istanbul'),
            self.date_done
        )
        values = {
            'ubl_version_id': UBL_VERSION_ID,
            'customization_id': CUSTOMIZATION_ID,
            'uuid': dispatch_uuid,
            'copy_indicator': 'false',
            'picking': self,
            'current_company': self.env.company.partner_id,
            'issue_date': scheduled_date_local.date().strftime('%Y-%m-%d'),
            'issue_time': scheduled_date_local.time().strftime('%H:%M:%S'),
            'actual_date': date_done_local.strftime('%Y-%m-%d'),
            'actual_time': date_done_local.strftime('%H:%M:%S'),
            'line_count': len(self.move_ids_without_package),
            'printed_date': self.l10n_tr_nilvera_delivery_date and self.l10n_tr_nilvera_delivery_date.strftime('%Y-%m-%d'),
            'drivers': drivers,
            'default_tckn': DEFAULT_TCKN
        }
        xml_content = self.env['ir.qweb']._render(
            'l10n_tr_nilvera_edispatch.l10n_tr_edispatch_format',
            values
        )
        xml_string = etree.tostring(
            cleanup_xml_node(xml_content),
            pretty_print=False,
            encoding='UTF-8',
        )
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}_e_Dispatch.xml",
            'datas': base64.b64encode(xml_string),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })
        self.message_post(
            body=_("e-Dispatch XML file generated successfully."),
            attachment_ids=[attachment.id],
            subtype_xmlid='mail.mt_note'
        )

    def action_export_l10n_tr_delivery_note(self):
        errors = []
        for picking in self:
            if picking.country_code == 'TR' and picking.picking_type_code == 'outgoing':
                picking._l10n_tr_validate_edelivery_fields()
                if picking.l10n_tr_nilvera_edispatch_warnings:
                    errors.append(picking.name)
                else:
                    picking._l10n_tr_export_delivery_note()
        if len(self) > 1 and errors:
            raise UserError(_("Error occured in generating following records:\n- %s", '\n- '.join(errors)))

    def action_mark_l10n_tr_edispatch_status(self):
        self.filtered(
            lambda p: p.country_code == 'TR' and p.picking_type_code == 'outgoing'
        ).l10n_tr_nilvera_dispatch_state = 'sent'
