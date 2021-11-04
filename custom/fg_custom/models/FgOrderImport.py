# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import mimetypes
import base64
import logging


from odoo.tools import config, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat
logger = logging.getLogger(__name__)

class PosOrderInherit(models.Model):
    _inherit = "pos.order"
    _description = "inherit pos.order"

    #point_of_sale.view_pos_pos_form
    x_ext_order_ref = fields.Char("Order Ref")
    x_ext_source = fields.Char("Source")


class FgImportOrders(models.TransientModel):
    _name = 'fg.custom.import.order'
    _description = 'Order Import from Files'

    order_file = fields.Binary(
        string='CSV Format', required=True)
    order_filename = fields.Char(string='Filename')



    def cancel_button(self):

        return {
            'name': _('Import Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'fg.custom.import.order',
            'target': 'inline'
        }


    @api.onchange('order_file')
    def order_file_change(self):
        if self.order_filename and self.order_file:
            filetype = mimetypes.guess_type(self.order_filename)
            logger.info('Order file mimetype: %s', filetype)
            if filetype and filetype[0] not in ('text/csv', 'text/plain', 'application/vnd.ms-excel'):

                return {'warning': {
                    'title': _('Unsupported file format'),
                    'message': _(
                        "This file '%s' is not recognised as a CSV. "
                        "Please check the file and it's "
                        "extension.") % self.order_filename
                    }}

    def import_order_button(self):
        self.ensure_one()
        orders = self._read_csv_and_validate()
        if orders:
            returnMessage = self._post_orders(orders)
            returnMessage = "Orders are successfully uploaded to POS. \n" + returnMessage
            message_id = self.env['fg.message.wizard'].create({'message': _(returnMessage)})
            return {
                'name': _('Successfull'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'fg.message.wizard',
                'res_id': message_id.id,
                'target': 'new'
            }

    @api.model
    def _read_csv_and_validate(self):
        jsonOrders = []
        try:
            orderfile = base64.b64decode(self.order_file)
            orderfile_string = orderfile.decode('utf-8')
            # data = json.loads(file_string)
            orders = orderfile_string.split('\r\n')
            notNotFound = None
            notNotFoundInPOS = None

            duplicateRef = None #duplicate orders

            orderReferencesSesion = None  # hold order ref for session not found
            customerNames = None

            noCustomerNames=None

            header = True
            # data in sheet
            # col[0] = company
            # col[1] = session
            # col[2] = order ref
            # col[3] = source
            # col[4] = customer
            # col[5] = customer email
            # col[6] = item name
            # col[7] = item code
            # col[8] = price
            # col[9] = discount
            # col[10] = quantity
            # col[11] = Total Line Amount
            # col[12] = Total Order Amount
            # col[13] = Amount Paid
            # validate data
            for row in orders:
                hasErrors = False
                if not header:
                    orderLine = row.split(',')
                    if len(orderLine) > 1:
                        # check items if exist
                        sku = orderLine[7]
                        product_template = self.env['product.template'].search([('default_code', '=', sku)])
                        if not product_template:
                            hasErrors = True
                            if not notNotFound:
                                notNotFound = sku
                            else:
                                if sku not in notNotFound:
                                    notNotFound += ", " + sku
                        elif not product_template.available_in_pos:
                            hasErrors = True
                            if not notNotFoundInPOS:
                                notNotFoundInPOS = sku
                            else:
                                if sku not in notNotFoundInPOS:
                                    notNotFoundInPOS += ", " + sku

                        # check duplicate orders
                        orderRef = orderLine[2]
                        orderSource = orderLine[3]
                        orderexist = None
                        if (orderSource + ' ' +orderRef) not in duplicateRef:
                            orderexist = self.env['pos.order'].search([('x_ext_order_ref', '=', orderRef), ('x_ext_source', '=', orderSource)])
                        if orderexist:
                            hasErrors = True
                            if not duplicateRef:
                                duplicateRef = orderSource + ' ' +orderRef
                            else:
                                duplicateRef += ", " + orderSource + ' ' +orderRef

                        # check company + session
                        comp = orderLine[0]
                        sess = orderLine[1]
                        company = self.env['res.company'].search([('name', '=', comp)])
                        session_id = ''
                        if company:
                            session = self.env['pos.session'].search([('name', '=', sess), ('state', '=', 'opened')])
                            config = session.config_id
                            session_company = config.company_id
                            if session and company:
                                session_id = session.id
                                if not session_company.id == company.id:
                                    hasErrors = True
                                    if (orderSource + ' ' +orderRef) not in orderReferencesSesion:
                                        if not orderReferencesSesion:
                                            orderReferencesSesion = orderSource + ' ' +orderRef
                                        else:
                                            orderReferencesSesion += ", " + orderSource + ' ' +orderRef
                            else:
                                hasErrors = True
                                if (orderSource + ' ' +orderRef) not in orderReferencesSesion:
                                    if not orderReferencesSesion:
                                        orderReferencesSesion = orderSource + ' ' +orderRef
                                    else:
                                        orderReferencesSesion += ", " + orderSource + ' ' +orderRef

                        elif (orderSource + ' ' +orderRef) not in orderReferencesSesion:
                            hasErrors = True
                            if not orderReferencesSesion:
                                orderReferencesSesion = orderSource + ' ' +orderRef
                            else:
                                orderReferencesSesion += ", " + orderSource + ' ' +orderRef


                        #check customer
                        customer_id = None
                        cust = orderLine[4]
                        custEmail = orderLine[5]
                        customer = None
                        customer = self.env['res.partner'].search([('name', '=', cust)])
                        if cust not in customerNames:
                            if not customer:
                                customer = self.env['res.partner'].search([('email', '=', custEmail)])
                                if not customer:
                                    #create customer
                                    customer = {"name": cust, "email": custEmail, "is_company": False}
                                    customer = self.env['res.partner'].create(customer)
                                    # hasErrors = True
                                    # if customerNames == '':
                                    #     customerNames = cust
                                    # else:
                                    #     customerNames += ", " + cust
                            customerNames += ', ' + cust
                        if customer:
                            customer_id = customer.id

                        if not customer_id:
                            if (orderSource + ' ' +orderRef) not in noCustomerNames:
                                if not noCustomerNames:
                                    noCustomerNames = orderSource + ' ' +orderRef
                                else:
                                    noCustomerNames += ", " + orderSource + ' ' +orderRef

                        #convert to json if no errors
                        if not hasErrors:
                            itemDescription = orderLine[6]
                            price = float(orderLine[8])
                            quantity = float(orderLine[9])
                            totalLineAmount = float(orderLine[10])
                            discount = float(orderLine[11])
                            totalOrderAmount = float(orderLine[12])
                            amountPaid = float(orderLine[13])
                            jsonOrder = {
                                            "company": company.id,
                                            "session": session_id,
                                            "orderRef": orderRef,
                                            "orderSource": orderSource,
                                            "itemDescription": itemDescription,
                                            "itemCode": sku,
                                            "productTemplate": product_template.id,
                                            "price": price,
                                            "discount": discount,
                                            "quantity": quantity,
                                            "totalLineAmount": totalLineAmount,
                                            "totalOrderAmount": totalOrderAmount,
                                            "amountPaid": amountPaid,
                                            "priceListId": config.pricelist_id.id,
                                            "fiscalPositionId": config.default_fiscal_position_id.id,
                                            "customer": customer_id
                                         }
                            jsonOrders.append(jsonOrder)
                header = False
            errorMsg = ''
            if not notNotFound:
                errorMsg += "Items not found: " + notNotFound

            if not notNotFoundInPOS:
                errorMsg += "\nItems found but not available in POS: " + notNotFoundInPOS

            if not duplicateRef:
                errorMsg += "\nDuplicate orders: " + duplicateRef


            if not orderReferencesSesion:
                errorMsg += "\nError in Company and Session data for order ref: " + orderReferencesSesion


            if not noCustomerNames:
                errorMsg += "\nNo customer specified in order/s: " + noCustomerNames

            if errorMsg != '':
                errorMsg += '\n\nPlease correct these errors and re-upload.'
                raise ValidationError(errorMsg)
            else: #check orders if sorted well haha
                orderRef = ''
                orderSource = ''
                orderReferences = ''
                for order in jsonOrders:
                    # save first or new header
                    orderRefSource = order['orderSource'] + order['orderRef']
                    if orderRef == '' or orderRef != orderRefSource:
                        if orderRefSource not in orderReferences:
                            orderReferences +=", " +  orderRefSource
                        else:
                            errorMsg = "References and sources should be in order."
                            break
                    orderRef = order['orderSource'] + order['orderRef']
                if errorMsg != '':
                    errorMsg += '\n\nPlease correct these errors and re-upload.'
                    raise ValidationError(errorMsg)

        except ValueError:
            raise ValidationError(ValueError)

        return jsonOrders




    @api.model
    def _post_orders(self, orders):
        returnMessage=''
        orderRef = '' #order ref holder
        orderId = '' #order id holder
        orderLines=[]
        count = 1
        orderLinesCount=0;
        orderCount=0;
        for order in orders:
            #save first or new header
            if orderRef != '' and orderRef != (order['orderSource']+order['orderRef']):
                #get the previous order
                prevOrder = orders[count-2]
                session = self.env['pos.session'].search([('id', '=', prevOrder['session'])])
                savedOrder = self._post_order(prevOrder, orderLines, session)
                orderLinesCount += len(orderLines)
                orderCount += 1
                orderLines = []
            orderLine = [
                            0,
                            0,
                            {
                                "product_id": order['productTemplate'],
                                "price_unit": order['price'],
                                "qty": order['quantity'],
                                "price_subtotal": order['totalLineAmount'],
                                "price_subtotal_incl": order['totalLineAmount'],
                                "discount": order['discount'],
                                "full_product_name": order['itemDescription'],
                                "tax_ids": [
                                    [
                                        6, False,
                                        []
                                    ]
                                ]
                            }
                        ]
            orderLines.append(orderLine)
            orderRef = order['orderSource']+order['orderRef']

            #check if this is the last row
            if len(orders) == count:
                #get the previous order

                session = self.env['pos.session'].search([('id', '=',  order['session'])])
                savedOrder = self._post_order(order, orderLines, session)
                orderLinesCount += len(orderLines)
                orderCount += 1
            count = count+1

        returnMessage = "Total: " + str(orderCount) +' orders with ' + str(orderLinesCount) + " order lines."

        return returnMessage

    @api.model
    def get_import_templates(self):
        return {
            'label': _('Import Template for POS Orders'),
            'template': '/fg_custom/static/csv/pos_order_template.csv'
        }

    @api.model
    def _post_order(self, order, orderLines, session):

        lastOrder  = self.env['pos.order'].search([('sequence_number', '!=', 0)],  order='sequence_number desc', limit=1)
        sequence=1
        if lastOrder:
            sequence = lastOrder.sequence_number + 1
        posReference = self._zero_pad(session.id, 5) + '-' + self._zero_pad(session.login_number, 3) + '-' + self._zero_pad(sequence, 4)
        posReference = 'Order ' + posReference
        orderHeader = {
            "company_id": order['company'],
            "pos_reference":posReference,
            "user_id": self.env.user.id,
            "session_id": order['session'],
            "amount_total": order['totalOrderAmount'],
            "amount_paid": order['amountPaid'],
            "amount_tax": 0,
            "amount_return": 0,
            "to_invoice": False,
            "is_tipped": False,
            "to_ship": False,
            "tip_amount": 0,
            "x_ext_order_ref": order['orderRef'],
            "x_ext_source": order['orderSource'],
            "x_total_so_pwd": 0,
            "pricelist_id": order['priceListId'],
            "fiscal_position_id": order['fiscalPositionId'],
            "partner_id": order['customer'],
            "sequence_number": sequence,
            "lines": orderLines
        }
        savedOrder = self.env['pos.order'].create(orderHeader)

        dateNow = fields.Datetime.now()
        orderHeader = {
            "company_id": order['company'],
            "pos_reference": posReference,
            "user_id": self.env.user.id,
            "session_id": order['session'],
            "amount_total": order['totalOrderAmount'],
            "amount_paid": order['amountPaid'],
            "amount_tax": 0,
            "amount_return": 0,
            "to_invoice": False,
            "is_tipped": False,
            "to_ship": False,
            "tip_amount": 0,
            "x_ext_order_ref": order['orderRef'],
            "x_ext_source": order['orderSource'],
            "x_total_so_pwd": 0,
            "pricelist_id": order['priceListId'],
            "fiscal_position_id": order['fiscalPositionId'],
            "partner_id": order['customer'],
            "sequence_number": sequence,
            "statement_ids": [
                [
                    0,
                    0,
                    {
                        "name": dateNow,
                        "payment_method_id": 1,
                        "amount": order['amountPaid'],
                        "payment_status": "",
                        "ticket": "",
                        "card_type": "",
                        "cardholder_name": "",
                        "transaction_id": ""
                    }
                ]
            ],
            "lines": orderLines
        }
        # process payment
        processPayment = self.env['pos.order']._process_payment_lines(orderHeader, savedOrder, session, False)
        savedOrder.write({'state': 'paid'})
        return savedOrder

    @api.model
    def _zero_pad(self, num, size):
        s = ""+ str(num)
        while len(s) < size:
            s = "0" + s
        return s
