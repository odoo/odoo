# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import mimetypes
import base64
import logging
import io
import csv

from odoo.tools import config, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat
logger = logging.getLogger(__name__)

class PosOrderInherit(models.Model):
    _inherit = "pos.order"
    _description = "inherit pos.order"

    #point_of_sale.view_pos_pos_form
    x_ext_order_ref = fields.Char("External Order Ref")
    x_ext_source = fields.Char("Channel")
    x_receipt_note = fields.Char("Receipt Note")
    x_receipt_printed = fields.Boolean("Is Receipt Printed")
    x_receipt_printed_date = fields.Date("OR Printed Date")
    x_receipt_printed_date = fields.Date("OR Printed Date")
    website_order_id = fields.Char("Website Order ID")


    pos_trans_reference = fields.Char(string='Trans Receipt Number', readonly=True, copy=False) # trans # for order/refund
    pos_si_trans_reference = fields.Char(string='SI Receipt Number', copy=False) # si # for order
    pos_refund_si_reference = fields.Char(string='Refund SI Receipt Number', readonly=True, copy=False) #si # for refund

    pos_refunded_id = fields.Many2one('pos.order', string='Order')


    def create(self, vals):
        res = super(PosOrderInherit, self).create(vals)
        for i in res:
            i.pos_trans_reference = self.env.ref('fg_custom.seq_pos_trans').next_by_id()
            if i.refunded_orders_count > 0:
                i.pos_refund_si_reference = self.env.ref('fg_custom.seq_pos_refund_si').next_by_id()
                order = i.refunded_order_ids[0]
                i.pos_refunded_id = order
            else:
                i.pos_si_trans_reference = self.env.ref('fg_custom.seq_pos_si_trans').next_by_id()
        return res

    def get_si_trans_sequence_number(self, name):
        if name:
            order = self.search([('pos_reference', '=', name)], limit=1)
            if order:
                pos_trans_reference = order.pos_trans_reference
                pos_refunded_id = False
                pos_si_trans_reference = False
                pos_refund_si_reference = False
                if order.pos_refunded_id:
                    pos_refunded_id = order.pos_refunded_id.pos_si_trans_reference
                    pos_refund_si_reference = order.pos_refund_si_reference
                else:
                    pos_si_trans_reference = order.pos_si_trans_reference
                return {
                    'pos_trans_reference': pos_trans_reference,
                    'pos_refunded_id': pos_refunded_id,
                    'pos_refund_si_reference': pos_refund_si_reference,
                    'pos_si_trans_reference': pos_si_trans_reference
                }
        else:
            return False

class PosOrderLineInherit(models.Model):
    _inherit = "pos.order.line"
    
    is_non_zero_vat = fields.Selection(string="Is Vat (V)", readonly=True,
                                       selection=[('is_vat', 'Is Vat (V)'), ('is_non_vat', 'Is Non Vat (E)'),
                                                  ('is_zero_vat', 'Is Zero Vat (Z)')], store=True)

    @api.depends('price_unit', 'tax_ids', 'qty', 'discount', 'product_id', 'tax_ids_after_fiscal_position')
    def _compute_is_non_zero_vat(self):
        for line in self:
            is_non_zero_vat = False
            for tax in line.tax_ids_after_fiscal_position:
                is_non_zero_vat = tax.is_non_zero_vat
            line.is_non_zero_vat = is_non_zero_vat

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

    @api.model
    def _read_csv_and_validate2(self):
        csv_data = base64.b64decode(self.order_file)
        data_file = io.StringIO(csv_data.decode("utf-8"))
        data_file.seek(0)
        file_reader = []
        csv_reader = csv.reader(data_file, delimiter=',')
        file_reader.extend(csv_reader)
        for f in file_reader:
            print(f[0])

    def import_order_button(self):
        self.ensure_one()
        ordersDetails = self._read_csv_and_validate()
        if ordersDetails:
            returnMessage = self._post_orders(ordersDetails)
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
        #try:
        orderfile = base64.b64decode(self.order_file)
        data_file = io.StringIO(orderfile.decode("utf-8"))
        data_file.seek(0)
        orders = []
        csv_reader = csv.reader(data_file, delimiter=',')
        orders.extend(csv_reader)

        notNotFound = ''
        notNotFoundInPOS = ''

        duplicateSKUS = ''

        duplicateRef = '' #duplicate orders

        orderReferencesSesion = ''  # hold order ref for session not found
        customerNames = ''

        noCustomerNames=''


        giftCardPaymentNumber=''

        header = True
        # data in sheet
        # col[0] = company
        # col[1] = session
        # col[2] = order ref
        # col[3] = source
        # col[4] = customer
        # col[5] = customer email

        # col[6] = phone
        # col[7] = street
        # col[8] = city
        # col[9] = zip

        # col[10] = item code
        # col[11] = item desc
        # col[12] = price
        # col[13] = quantity
        # col[14] = Total Order Discount
        # col[15] = Type
        # col[16] = Card
        # col[17] = Amount Paid
        # validate data
        paymentList=[]
        for orderLine in orders:
            hasErrors = False
            if not header:
                if len(orderLine) > 1:

                    orderRef = orderLine[2]
                    orderSource = orderLine[3]
                    sku = orderLine[10]
                    cust = orderLine[4]
                    if sku != 'Payment':
                        price = float(orderLine[12])
                        quantity = float(orderLine[13])
                        if not orderRef or not orderSource or not sku or not cust or not price or not quantity:
                            raise ValidationError("Please make sure required values are field in. " + orderRef)

                    amount = None
                    #check needed fields
                    if sku == 'Payment': #default Cash
                        type = 'Cash'
                        amountPaid = orderLine[17]
                        notes = orderLine[18]
                        cardNumber = None
                        if orderLine[15] == 'Gift Card':
                            type=orderLine[15]
                            cardNumber = orderLine[16]
                            if not amountPaid:
                                hasErrors = True
                                if orderRef not in giftCardPaymentNumber:
                                    if giftCardPaymentNumber == '':
                                        giftCardPaymentNumber = orderRef
                                    else:
                                        if sku not in giftCardPaymentNumber:
                                            giftCardPaymentNumber += ", " + orderRef

                        #get payment method
                        paymentMethod = self.env['pos.payment.method'].search([('name', '=', type),('active', '=', True)])
                        if not paymentMethod or not amountPaid:
                            if giftCardPaymentNumber == '':
                                giftCardPaymentNumber = orderRef
                            else:
                                if sku not in giftCardPaymentNumber:
                                    giftCardPaymentNumber += ", " + orderRef
                        else:
                            payment = {
                                "orderRef": orderRef,
                                "orderSource": orderSource,
                                "type": type,
                                "cardNumber": cardNumber,
                                "amountPaid": amountPaid,
                                "paymentMethod": paymentMethod,
                                "notes": notes
                            }
                            paymentList.append(payment)
                    else:
                        # check items if exist
                        product_template = None
                        product_template = self.env['product.template'].search([('default_code', '=', sku)])
                        if len(product_template) > 1:
                            hasErrors = True
                            if duplicateSKUS == '':
                                duplicateSKUS = sku
                            else:
                                if sku not in duplicateSKUS:
                                    duplicateSKUS += ", " + sku
                        else:
                            if not product_template:
                                hasErrors = True
                                if notNotFound == '':
                                    notNotFound = sku
                                else:
                                    if sku not in notNotFound:
                                        notNotFound += ", " + sku
                            elif not product_template.available_in_pos:
                                hasErrors = True
                                if notNotFoundInPOS == '':
                                    notNotFoundInPOS = sku
                                else:
                                    if sku not in notNotFoundInPOS:
                                        notNotFoundInPOS += ", " + sku

                        # check duplicate orders
                        orderexist = None
                        if (orderSource + ' ' +orderRef) not in duplicateRef:
                            orderexist = self.env['pos.order'].search([('x_ext_order_ref', '=', orderRef), ('x_ext_source', '=', orderSource)])
                        if orderexist:
                            hasErrors = True
                            if duplicateRef == '':
                                duplicateRef = orderSource + ' ' +orderRef
                            else:
                                duplicateRef += ", " + orderSource + ' ' +orderRef

                        # check company + session
                        comp = orderLine[0]
                        sess = orderLine[1]
                        company = self.env['res.company'].search([('name', '=', comp)])
                        session_id = ''
                        if company:
                            session = self.env['pos.session'].search([('name', '=', sess),('state', '=', 'opened')])
                            config = session.config_id
                            session_company = config.company_id
                            if session and company:
                                session_id = session.id
                                if not session_company.id == company.id:
                                    hasErrors = True
                                    if (orderSource + ' ' +orderRef) not in orderReferencesSesion:
                                        if orderReferencesSesion == '':
                                            orderReferencesSesion = orderSource + ' ' +orderRef
                                        else:
                                            orderReferencesSesion += ", " + orderSource + ' ' +orderRef
                            else:
                                hasErrors = True
                                if (orderSource + ' ' +orderRef) not in orderReferencesSesion:
                                    if orderReferencesSesion == '':
                                        orderReferencesSesion = orderSource + ' ' +orderRef
                                    else:
                                        orderReferencesSesion += ", " + orderSource + ' ' +orderRef

                        elif (orderSource + ' ' +orderRef) not in orderReferencesSesion:
                            hasErrors = True
                            if orderReferencesSesion == '':
                                orderReferencesSesion = orderSource + ' ' +orderRef
                            else:
                                orderReferencesSesion += ", " + orderSource + ' ' +orderRef


                        #check customer
                        customer_id = None

                        custEmail = orderLine[5]
                        phone = orderLine[6]
                        street = orderLine[7]
                        city = orderLine[8]
                        zip = orderLine[9]
                        customer = None
                        customer = self.env['res.partner'].search([('name', '=', cust)])
                        if cust not in customerNames:
                            if not customer:
                                if custEmail!=False and custEmail != '':
                                    customer = self.env['res.partner'].search([('email', '=', custEmail)])
                                if not customer:
                                    #create customer
                                    customer = {"name": cust,
                                                "email": custEmail,
                                                "phone": phone,
                                                "street": street,
                                                "city": city,
                                                "zip": zip,
                                                "is_company": False
                                                }
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
                                if noCustomerNames == '':
                                    noCustomerNames = orderSource + ' ' +orderRef
                                else:
                                    noCustomerNames += ", " + orderSource + ' ' +orderRef

                        #convert to json if no errors
                        if not hasErrors:
                            itemDescription = orderLine[11]
                            discount = 0
                            if orderLine[14]:
                               discount = float(orderLine[14])

                            taxes = product_template.taxes_id

                            notes = orderLine[14]

                            #get in product_product
                            product_product = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)])

                            jsonOrder = {
                                            "company": company.id,
                                            "session": session_id,
                                            "orderRef": orderRef,
                                            "orderSource": orderSource,
                                            "itemDescription": itemDescription,
                                            "itemCode": sku,
                                            "product": product_product,
                                            "price": price,
                                            "discount": discount,
                                            "quantity": quantity,
                                            "priceList": config.pricelist_id,
                                            "fiscalPositionId": config.default_fiscal_position_id.id,
                                            "customerId": customer_id,
                                            "taxes": taxes
                                         }
                            jsonOrders.append(jsonOrder)

            header = False
        errorMsg = ''
        if notNotFound != '':
            errorMsg += "Items not found: " + notNotFound

        if notNotFoundInPOS != '':
            errorMsg = "\n\nItems found but not available in POS: " + notNotFoundInPOS

        if duplicateSKUS != '':
            errorMsg += "\n\nDuplicate SKU setup: " + duplicateSKUS

        if duplicateRef != '':
            errorMsg += "\n\nDuplicate orders: " + duplicateRef


        if orderReferencesSesion != '':
            errorMsg += "\n\nError in Company and Session data for order ref: " + orderReferencesSesion


        if noCustomerNames != '':
            errorMsg += "\n\nNo customer specified in order/s: " + noCustomerNames


        if giftCardPaymentNumber != '':
            errorMsg += "\n\nEither card#, paid amount or payment method is not available for order ref: " + giftCardPaymentNumber

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

        #except ValueError:
        #    raise ValidationError(ValueError)

        ordersDetails = {"orders": jsonOrders, "paymentList": paymentList}
        return ordersDetails




    @api.model
    def _post_orders(self, ordersDetails):
        returnMessage=''
        orderRef = '' #order ref holder
        orderId = '' #order id holder
        orderLines=[]
        count = 1
        orderLinesCount=0;
        orderCount=0;
        orders = ordersDetails['orders']
        paymentList = ordersDetails['paymentList']
        for order in orders:
            #save first or new header
            if orderRef != '' and orderRef != (order['orderSource']+order['orderRef']):
                #get the previous order
                prevOrder = orders[count-2]
                session = self.env['pos.session'].search([('id', '=', prevOrder['session'])])
                paymentList = self._post_order(prevOrder, orderLines, session,paymentList)
                orderLinesCount += len(orderLines)
                orderCount += 1
                orderLines = []
            computeAmount = self._compute_amount(order)

            orderLine = [
                            0,
                            0,
                            {
                                "product_id": order['product'].id,
                                "price_unit": order['price'],
                                "qty": order['quantity'],
                                "price_subtotal": computeAmount['priceSubTotal'],
                                "price_subtotal_incl": computeAmount['priceTotalIncl'],
                                "discount": order['discount'],
                                "full_product_name": order['itemDescription'],
                                "tax_ids": [
                                    [
                                        6, False,
                                        [x.id for x in order['taxes']]
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
                savedOrder = self._post_order(order, orderLines, session, paymentList)
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
    def _post_order(self, order, orderLines, session, paymentList):

        lastOrder  = self.env['pos.order'].search([('sequence_number', '!=', 0)],  order='sequence_number desc', limit=1)
        sequence = 1
        if lastOrder:
            sequence = lastOrder.sequence_number + 1
        posReference = self._zero_pad(session.id, 5) + '-' + self._zero_pad(session.login_number, 3) + '-' + self._zero_pad(sequence, 4)
        posReference = 'Order ' + posReference
        total = self._compute_total(orderLines)

        amountPaid = 0
        notes = ''
        # get paymenlist
        statementIds = []
        dateNow = str(fields.Datetime.now())
        paymentIndexes = []
        paymentIndex=0
        for payment in paymentList:
            if (order['orderRef'] == payment['orderRef']) and (order['orderSource'] == payment['orderSource']):
                statementId = {
                    "name": dateNow,
                    "payment_method_id": payment['paymentMethod'].id,
                    "amount": payment['amountPaid'],
                    "payment_status": "",
                    "ticket": "",
                    "card_type": "",
                    "cardholder_name": "",
                    "transaction_id": "",
                    "x_gift_card_number": payment['cardNumber']
                }
                notes = payment['notes']
                amountPaid += float(payment['amountPaid'])
                statementIds.append([0, 0, statementId])
                paymentIndexes.append(paymentIndex)
            paymentIndex += 1

        #remove paymentList
        paymentIndex = 0
        for index in paymentIndexes:
            paymentList.pop(index-paymentIndex)
            paymentIndex += 1

        orderHeader = {
            "company_id": order['company'],
            "pos_reference": posReference,
            "user_id": self.env.user.id,
            "session_id": order['session'],
            "amount_total": total['amountTotal'],
            "amount_paid": amountPaid,
            "amount_tax":  total['totalTax'],
            "amount_return": 0,
            "to_invoice": False,
            "is_tipped": False,
            "to_ship": False,
            "tip_amount": 0,
            "x_ext_order_ref": order['orderRef'],
            "x_ext_source": order['orderSource'],
            "x_total_so_pwd": 0,
            "x_receipt_note": notes,
            "pricelist_id": order['priceList'].id,
            "fiscal_position_id": order['fiscalPositionId'],
            "partner_id": order['customerId'],
            "sequence_number": sequence,
            "lines": orderLines
        }
        savedOrder = self.env['pos.order'].create(orderHeader)


        orderHeader = {
            "company_id": order['company'],
            "pos_reference": posReference,
            "user_id": self.env.user.id,
            "session_id": order['session'],
            "amount_total": total['amountTotal'],
            "amount_paid": amountPaid,
            "amount_tax":  total['totalTax'],
            "amount_return": 0,
            "to_invoice": False,
            "is_tipped": False,
            "to_ship": False,
            "tip_amount": 0,
            "x_ext_order_ref": order['orderRef'],
            "x_ext_source": order['orderSource'],
            "x_total_so_pwd": 0,
            "pricelist_id": order['priceList'].id,
            "fiscal_position_id": order['fiscalPositionId'],
            "partner_id": order['customerId'],
            "sequence_number": sequence,
            "statement_ids": statementIds,
            "lines": orderLines
        }

        # process payment
        processPayment = self.env['pos.order']._process_payment_lines(orderHeader, savedOrder, session, False)
        savedOrder.write({'state': 'paid'})

        try:
            savedOrder.action_pos_order_paid()
        except savedOrder.DatabaseError:
            # do not hide transactional errors, the order(s) won't be saved!
            raise
        except Exception as e:
            raise ValidationError(e);
        savedOrder._create_order_picking()
        savedOrder._compute_total_cost_in_real_time()


        return paymentList

    @api.model
    def _zero_pad(self, num, size):
        s = ""+ str(num)
        while len(s) < size:
            s = "0" + s
        return s


    @api.model
    def _compute_amount(self, orderLine):
        computeAmount = {}
        if orderLine['product']:
            price = float(orderLine['price']) * (1 - (float(orderLine['discount']) or 0.0) / 100.0)
            priceSubTotal= priceSubTotalIncl = price * float(orderLine['quantity'])
            taxIds =orderLine['taxes']
            priceList = orderLine['priceList']
            if (taxIds):
                taxes = taxIds.compute_all(price, priceList.currency_id, float(orderLine['quantity']), product=orderLine['product'], partner=False)
                priceSubTotal = taxes['total_excluded']
                priceSubTotalIncl = taxes['total_included']
            computeAmount = {"priceSubTotal": priceSubTotal, "priceTotalIncl": priceSubTotalIncl}
        return computeAmount

    @api.model
    def _compute_total(self, orderLines):
        totalTax = 0
        amountTotal = 0
        for orderLine in orderLines:
            totalTax += orderLine[2]['price_subtotal_incl'] - orderLine[2]['price_subtotal']
            amountTotal += orderLine[2]['price_subtotal_incl']
        return {"amountTotal": amountTotal,"totalTax": totalTax}
