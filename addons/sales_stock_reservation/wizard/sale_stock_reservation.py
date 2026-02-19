# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models
from odoo.http import request


class SaleStockReservation(models.TransientModel):
    """
    This model is used to reserve products for a sale order.

    Fields:
    - stock_reservation_ids: A one-to-many relationship to the
     `stock.reservation` model, representing the reservations to be made.
    - sale_order_id: The ID of the sale order for which the products are being
      reserved.
    - mail_notification_ids: A many-to-many relationship to the `res.users`
      model,representing the users who should receive email notifications about
      the reservation.
    """
    _name = "sale.stock.reservation"
    _description = "Stock Reservation"

    stock_reservation_ids = fields.One2many(
        "stock.reservation",
        "stock_reservation_wizard_id",
        string="Order line",
        help='This is a One2many field that refers to the reserved stock items '
             'associated with the wizard.')
    sale_order_id = fields.Many2one(
        "sale.order", string="Sale order",
        readonly="True",
        help="Many2one field that returns the Sale Order")
    mail_notification_ids = fields.Many2many(
        "res.users",
        string="Email Notification",
        help='This is a Many2many field that refers to the users '
             'who will receive email notifications.')

    def action_reserve_stock(self):
        """
         This function reserves stock for a sale order and creates a stock
         reservation.

         The function sets the state of the associated sale order to "reserved".

         It then retrieves the source and destination locations for the stock
         reservation from the system parameters.

         For each product in the stock reservation, the function creates a
         stock move to transfer the product from the source location to the
         destination location, sets the reservation status for the product, and
         updates the stock reservation with the ID of the newly created stock
         move.

         The function then creates a new record for each reserved product and
         adds it to the `reserved_stock_ids` field of the associated sale order.

         Finally, if there are any mail notifications associated with the stock
         reservation,the function sends an email to each recipient with details
         of the reserved items.

         :return: None
         """
        self.sale_order_id.state_reservation = "reserved"
        source_location = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'sales_stock_reservation.source_location_id'))
        destination_location = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'sales_stock_reservation.destination_location_id'))
        for rec in self.stock_reservation_ids:
            move_vals = {
                "name": "Product Quantity Reserved",
                "location_id": source_location,
                "location_dest_id": destination_location,
                'product_id': rec.product_id.id,
                "product_uom_qty": rec.reserve_quantity,
                "date": fields.Datetime.now(),
                "product_uom": rec.unit_of_measure_id.id
            }
            move = self.env["stock.move"].create(move_vals)
            rec.move_id = move.id
            move._action_confirm()
            move._action_assign()
        line_vals = [{
            "order_line_name": rec.order_line_name,
            "product_id": rec.product_id.id,
            "reserved_quantity": rec.reserve_quantity,
            "sale_order_id": self.sale_order_id.id,
            "status": 'reserved',
            "move_id": rec.move_id.id
        } for rec in self.stock_reservation_ids]
        self.sale_order_id.write(
            {'reserved_stock_ids': [(0, 0, vals) for vals in line_vals]})
        if self.mail_notification_ids:
            for rec in self.mail_notification_ids:
                message_body = \
                    f"Dear {rec.name}, <br>" \
                    f"<br>We would like to inform you that, some item(s)" \
                    f" have been reserved for - {self.sale_order_id.name}." \
                    f" Please check and take necessary action if needed. <br> "
                message_body += \
                    '<table border="1" cellpadding="0" bgcolor="#ededed">'
                message_body += ('<tr><th width="250px;">Name</th>'
                                 '<th width="250px;">Product</th>'
                                 '<th width="250px;">Quantity for '
                                 'Reservation</th></tr>')
                for reserved in self.sale_order_id.reserved_stock_ids.filtered(
                        lambda r: r.status == 'reserved'):
                    message_body += f"<tr><td>{reserved.name}</td>" \
                                    f"<td>{reserved.product_id.name}</th>" \
                                    f"<td>{reserved.reserved_quantity}</td>" \
                                    f"</tr><br> "
                message_body += '</table>Thank you'
                template_obj = self.env['mail.mail'].create({
                    'subject': f"Stock Reservation: {self.sale_order_id.name}",
                    'body_html': message_body,
                    'email_from': request.env.user.company_id.email,
                    'email_to': rec.login
                })
                template_obj.send()
