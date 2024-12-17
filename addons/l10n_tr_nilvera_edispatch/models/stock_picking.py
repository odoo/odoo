import base64
import uuid
from lxml import etree
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_tr_nilvera_dispatch_type = fields.Selection(
        string="Dispatch Type",
        help="Used to populate the type of dispatch.",
        selection=[
            ('SEVK', "Online"),
            ('MATBUDAN', "Pre-printed"),
        ],
        default='SEVK',
        tracking=True,
    )
    l10n_tr_nilvera_carrier_id = fields.Many2one(
        string="Carrier (TR)",
        help="Used when the dispatch is made through a third-party carrier company. Populating this makes the Vehicle Plate and Drivers optional.",
        comodel_name='res.partner',
    )
    l10n_tr_nilvera_buyer_id = fields.Many2one(
        string="Buyer",
        help="Used for the original party who purchases the good when the Delivery Address is for another recipient",
        comodel_name='res.partner',
    )
    l10n_tr_nilvera_seller_supplier_id = fields.Many2one(
        string="Seller Supplier",
        help="Used for the information of the supplier of the goods in the delivery note.",
        comodel_name='res.partner',
    )
    l10n_tr_nilvera_buyer_originator_id = fields.Many2one(
        string="Buyer Originator",
        help="Used for the original initiator of the goods acquisition and requesting process.",
        comodel_name='res.partner',
    )
    l10n_tr_nilvera_delivery_printed_number = fields.Char(string="Printed Delivery Note Number")
    l10n_tr_nilvera_delivery_date = fields.Date(string="Printed Delivery Note Date")
    l10n_tr_vehicle_plate = fields.Many2one(
        string="Vehicle Plate",
        help="Used to input the plate number of the truck.",
        comodel_name='l10n_tr.nilvera.trailer.plate',
        domain="[('plate_number_type', '=', 'vehicle')]",
    )
    l10n_tr_nilvera_trailer_plate_ids = fields.Many2many(
        string="Trailer Plates",
        help="Used to input the plate numbers of the trailers attached to the truck.",
        comodel_name='l10n_tr.nilvera.trailer.plate',
        domain="[('plate_number_type', '=', 'trailer')]",
        relation='l10n_tr_nilvera_delivery_vehicle_rel',
    )
    l10n_tr_nilvera_driver_ids = fields.Many2many(
        string="Drivers",
        help="Used for the individuals driving the truck.",
        comodel_name='res.partner',
    )
    l10n_tr_nilvera_delivery_notes = fields.Char(string="Delivery Notes")
    l10n_tr_nilvera_dispatch_state = fields.Selection(
        string="e-Dispatch State",
        selection=[('to_send', "To Send"), ('sent', "Sent")],
        tracking=True,
    )
    l10n_tr_nilvera_edispatch_warnings = fields.Json(compute='_compute_edispatch_warnings')

    @api.depends(
        'l10n_tr_nilvera_carrier_id', 'l10n_tr_nilvera_buyer_id', 'l10n_tr_nilvera_seller_supplier_id',
        'l10n_tr_nilvera_buyer_originator_id', 'l10n_tr_nilvera_delivery_printed_number',
        'l10n_tr_nilvera_delivery_date', 'l10n_tr_vehicle_plate', 'l10n_tr_nilvera_trailer_plate_ids',
        'l10n_tr_nilvera_driver_ids', 'partner_id',
    )
    def _compute_edispatch_warnings(self):
        for picking in self:
            if picking.country_code == 'TR' and picking.picking_type_code == 'outgoing' and picking.state == 'done':
                picking.l10n_tr_nilvera_edispatch_warnings = picking._l10n_tr_validate_edispatch_fields()
            else:
                picking.l10n_tr_nilvera_edispatch_warnings = False

    def button_validate(self):
        res = super().button_validate()
        self.filtered(
            lambda p: p.country_code == 'TR' and p.state == 'done' and p.picking_type_code == 'outgoing'
        ).l10n_tr_nilvera_dispatch_state = 'to_send'
        return res

    def _l10n_tr_validate_edispatch_fields(self):
        self.ensure_one()

        if self.state != 'done':
            return {
                'invalid_transfer_state': {
                    'message': _("Please validate the transfer first to generate the XML"),
                }
            }
        partners = (
            self.company_id.partner_id
            | self.l10n_tr_nilvera_carrier_id
            | self.l10n_tr_nilvera_buyer_id
            | self.l10n_tr_nilvera_seller_supplier_id
            | self.l10n_tr_nilvera_buyer_originator_id
        )
        # `is_delivery_partner` ensures that Delivery Partner's ZIP is present regardless of the partner country.
        error_messages = self.partner_id._l10n_tr_nilvera_validate_partner_details(is_delivery_partner=True)
        partners = partners - self.partner_id
        error_messages.update(partners._l10n_tr_nilvera_validate_partner_details())

        if self.l10n_tr_nilvera_dispatch_type == 'MATBUDAN':
            if not self.l10n_tr_nilvera_delivery_date:
                error_messages['invalid_matbudan_date'] = {
                    'message': _("Printed Delivery Note Date is required."),
                }
            if (
                not self.l10n_tr_nilvera_delivery_printed_number
                or len(self.l10n_tr_nilvera_delivery_printed_number) != 16
            ):
                error_messages['invalid_matbudan_number'] = {
                    'message': _("Printed Delivery Note Number of 16 characters is required."),
                }

        invalid_country_drivers = self.l10n_tr_nilvera_driver_ids.filtered(
            lambda driver: not driver.country_id or driver.country_id.code != 'TR'
        )
        invalid_tckn_drivers = (self.l10n_tr_nilvera_driver_ids - invalid_country_drivers).filtered(
            lambda driver: not driver.vat or (driver.vat and len(driver.vat) != 11)
        )

        if drivers := len(invalid_country_drivers):
            error_messages['invalid_driver_country'] = {
                'message': _(
                    "Only Drivers from Türkiye are valid. Please update the Country and enter a valid TCKN in the Tax ID."
                ),
                'action_text': _(
                    "View %s",
                    (drivers == 1 and invalid_country_drivers.name) or _("Drivers"),
                ),
                'action': invalid_country_drivers._get_records_action(
                    name=_("Drivers"),
                ),
            }
        if drivers := len(invalid_tckn_drivers):
            driver_placeholder = drivers > 1 and _("Drivers") or _("%s's", invalid_tckn_drivers.name)
            error_messages['invalid_driver_tckn'] = {
                'message': _("%s TCKN is required.", driver_placeholder),
                'action_text': _("View %s", drivers == 1 and invalid_tckn_drivers.name or _("Drivers")),
                'action': invalid_tckn_drivers._get_records_action(name=_("Drivers")),
            }

        if (
            not self.l10n_tr_nilvera_carrier_id
            and not self.l10n_tr_nilvera_driver_ids
            and not self.l10n_tr_vehicle_plate
        ):
            error_messages['required_carrier_details'] = {
                'message': _("Carrier is required (optional when both the Driver and Vehicle Plate are filled)."),
            }

        elif not self.l10n_tr_nilvera_carrier_id and not self.l10n_tr_nilvera_driver_ids:
            error_messages['required_driver_details'] = {
                'message': _("At least one Driver is required."),
            }

        elif not self.l10n_tr_nilvera_carrier_id and not self.l10n_tr_vehicle_plate:
            error_messages['required_vehicle_details'] = {
                'message': _("Vehicle Plate is required."),
            }

        return error_messages or False

    def _l10n_tr_generate_edispatch_xml(self):
        dispatch_uuid = str(uuid.uuid4())
        drivers = []
        for driver in self.l10n_tr_nilvera_driver_ids:
            driver_name = driver.name.split(' ', 1)
            drivers.append({
                'name': driver_name[0],
                'fname': driver_name[1] if len(driver_name) > 1 else '\u200B',
                'tckn': driver.vat,
            })
        scheduled_date_local = fields.Datetime.context_timestamp(
            self.with_context(tz='Europe/Istanbul'),
            self.scheduled_date,
        )
        date_done_local = fields.Datetime.context_timestamp(
            self.with_context(tz='Europe/Istanbul'),
            self.date_done,
        )
        values = {
            'ubl_version_id': 2.1,
            'customization_id': 'TR1.2.1',
            'uuid': dispatch_uuid,
            'picking': self,
            'current_company': self.env.company.partner_id,
            'issue_date': scheduled_date_local.date().strftime('%Y-%m-%d'),
            'issue_time': scheduled_date_local.time().strftime('%H:%M:%S'),
            'actual_date': date_done_local.strftime('%Y-%m-%d'),
            'actual_time': date_done_local.strftime('%H:%M:%S'),
            'line_count': len(self.move_ids_without_package),
            'printed_date': self.l10n_tr_nilvera_delivery_date and self.l10n_tr_nilvera_delivery_date.strftime('%Y-%m-%d'),
            'drivers': drivers,
            'default_tckn': '22222222222',
            'dispatch_scenario': 'TEMELIRSALIYE',
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
            subtype_xmlid='mail.mt_note',
        )

    def action_generate_l10n_tr_edispatch_xml(self, is_list=False):
        errors = []
        for picking in self:
            if picking.country_code == 'TR' and picking.picking_type_code == 'outgoing':
                if picking._l10n_tr_validate_edispatch_fields():
                    errors.append(picking.name)
                else:
                    picking._l10n_tr_generate_edispatch_xml()
        if is_list and errors:
            raise UserError(_("Error occurred in generating XML for following records:\n- %s", '\n- '.join(errors)))

    def action_mark_l10n_tr_edispatch_status(self):
        self.filtered(
            lambda p: p.country_code == 'TR' and p.picking_type_code == 'outgoing'
        ).l10n_tr_nilvera_dispatch_state = 'sent'
