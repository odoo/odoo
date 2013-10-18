# -*- coding: utf-'8' "-*-"
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp
from openerp.osv import osv, fields
from openerp.tools import float_repr
import urlparse
import requests
import logging

_logger = logging.getLogger(__name__)


class Payment(osv.Model):
    _name = 'payment.transaction'
    _inherit = ['mail.thread']
    _order = 'id desc'

    _columns = {
        'create_date': fields.datetime('Creation Date', readonly=True, required=True),
        'partner_id': fields.related('creditcard_id', 'partner_id', type='many2one', relation='res.partner', readonly=True),
        'amount': fields.integer('Amount', required=True, help='in cents'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'reference': fields.char('Order Reference'),
        'acquirer_ref': fields.char('Payment Acquirer Ref'),
        'state': fields.selection([("pending", "Pending"),("validated", "Validated"),("refused", "Refused")], 'Status', required=True),
        'res_model': fields.char('Object Model'),
        'res_id': fields.char('Object Id'),
    }


class acquirer(osv.Model):
    _name = 'payment.acquirer'
    _description = 'Online Payment Acquirer'
    
    def list_acquirers(self, cr, uid, context=None):
        return [("virement", "Virement")]

    _columns = {
        'name': fields.char('Name', required=True),
        'acquirer': fields.selection(lambda self, *a, **k: self.list_acquirers(*a, **k), 'Acquirer', required=True),
        'form_template_id': fields.many2one('ir.ui.view', required=True), 
        'visible': fields.boolean('Visible', help="Make this payment acquirer available (Customer invoices, etc.)"),
    }

    def _check_required_if_acquirer(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids, context=context):
            if any(c for c, f in self._all_columns.items() if getattr(f.column, 'required_if_acquirer', None) == this.acquirer and not this[c]):
                return False
        return True

    _constraints = [
        (_check_required_if_acquirer, 'Required fields not filled', ['required for this payment acquirer']),
    ]

    _defaults = {
        'visible': True,
    }

    def render(self, cr, uid, id, object, reference, currency, amount, cancel_url=None, return_url=None, context=None):
        """ Renders the form template of the given acquirer as a qWeb template  """
        user = self.pool.get("res.users")
        precision = self.pool.get("decimal.precision").precision_get(cr, openerp.SUPERUSER_ID, 'Account')

        if not context:
            context = {}

        if isinstance(id, list):
            id = id[0]

        qweb_context = {}
        qweb_context.update(
            object=object,
            reference=reference,
            currency=currency,
            amount=amount,
            amount_str=float_repr(amount, precision),
            user_id=user.browse(cr, uid, uid),
            context=context,
            cancel_url=cancel_url,
            return_url=return_url
        )

        return self.browse(cr, uid, id, context=context) \
            .form_template_id.render(qweb_context, engine='ir.qweb', context=context) \
            .strip()

    def validate_payement(self, cr, uid, id, object, reference, currency, amount, context=None):
        """
        return (status, retry_time, log)
            status: "validated" or "refused" or "pending"
            retry_time = False (don't retry validation) or int (seconds for retry validation)
            log = str
        """

        if isinstance(id, list):
            id = id[0]

        pay = self.browse(cr, uid, id, context=context)
        method = getattr(self, '_validate_payement_%s' % pay.acquirer)
        status, retry_time, log = method(object, reference, currency, amount, context=context)


        # log transaction and payment
        if getattr(object, 'message_post'):
            object.message_post(cr, uid, False,
                body=log or "",
                subject="%s%s" % (status, retry_time and ": %s" % retry_time or ""),
                type='notification',
                context=context)

        if status == "validated":
            _logger.info("Payment Validate for %s:%s" % (object._name, reference) )
        elif status == "pending":
            _logger.debug("Payment Pending for %s:%s. Reason: %s" % (object._name, reference, log) )
        else:
            _logger.error("Payment Refused for %s:%s. Reason: %s" % (object._name, reference, log) )
        
        return (status, retry_time, log)

    def _validate_payement_virement(self, object, reference, currency, amount, context=None):
        return ("pending", False, "")

    def transaction_feedback(self, cr, uid, acquirer, context=None, **values):
        method = getattr(self, '_transaction_feedback_%s' % acquirer)
        return method(**values)


# paypal


class acquirer_paypal(osv.osv):
    _inherit = 'payment.acquirer'

    def list_acquirers(self, cr, uid, context=None):
        l = super(acquirer_paypal, self).list_acquirers(cr, uid, context)
        l.append(('paypal', 'Paypal'))
        return l

    def _validate_payement_paypal(self, object, reference, currency, amount, context=None):
        
        parameters = {}
        parameters.update(
            cmd='_notify-validate',
            business=object.company_id.paypal_account,
            item_name="%s %s" % (object.company_id.name, reference),
            item_number=reference,
            amount=amount,
            currency_code=currency.name
        )
        paypal_url = "https://www.paypal.com/cgi-bin/webscr"
        paypal_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
        response = urlparse.parse_qsl(requests.post(paypal_url, data=parameters))

        # transaction's unique id
        # response["txn_id"]

        # "Failed", "Reversed", "Refunded", "Canceled_Reversal", "Denied"
        status = "refused"
        retry_time = False

        if response["payment_status"] == "Voided":
            status = "refused"
        elif response["payment_status"] in ("Completed", "Processed") and response["item_number"] == reference and response["mc_gross"] == amount:
            status = "validated"
        elif response["payment_status"] in ("Expired", "Pending"):
            status = "pending"
            retry_time = 60

        return (status, retry_time, "payment_status=%s&pending_reason=%s&reason_code=%s" % (
                response["payment_status"], 
                response.get("pending_reason"), 
                response.get("reason_code")))

    def _transaction_feedback_paypal(self, **values):
        print values
        return True


# ogone


class acquirer_ogone(osv.Model):
    _name = 'payment.payment'

    _columns = {
        'ogone_3ds': fields.dummy('3ds activated'),
        'ogone_3ds_html': fields.text(),
        'ogone_feedback_model': fields.char(),
        'ogone_feedback_eval': fields.char(),

        # just for info
        'ogone_accepturl': fields.dummy(),
        'ogone_declineurl': fields.dummy(),
        'ogone_exceptionurl': fields.dummy(),

        'ogone_complus': fields.dummy(),
    }

    def _create_ogone(self, cr, uid, creditcard, values):
        currency = self.pool['res.currency'].browse(cr, uid, values['currency_id'])
        orderid = values.get('order_ref') or 'OE-ORDER-%s' % (time.time(),)
        account = creditcard.provider_account_id

        _logger.debug("Values %s", pformat(values))

        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'OrderID': orderid,
            'amount': values['amount'],
            'CURRENCY': currency.name,
            'OPERATION': 'SAL',
            'ECI': 2,   # Recurring (from MOTO)
            'ALIAS': creditcard.provider_ref,
            'RTIMEOUT': 30,
        }
        if creditcard.cvc:
            data['CVC'] = creditcard.cvc

        if values.pop('ogone_3ds', None):
            data.update({
                'FLAG3D': 'Y',   # YEAH!!
                'LANGUAGE': creditcard.partner_id.lang or 'en_US',
            })

            complus = values.get('ogone_complus')
            if complus:
                data['COMPLUS'] = complus

            for url in 'accept decline exception'.split():
                key = 'ogone_{0}url'.format(url)
                val = values.pop(key, None)
                if val:
                    key = '{0}URL'.format(url).upper()
                    data[key] = val

        _logger.debug("data %s", pformat(data))

        data['SHASIGN'] = _generate_ogone_shasign(account, 'in', data)

        direct_order_url = 'https://secure.ogone.com/ncol/%s/orderdirect.asp' % (account.ogone_env,)

        request = urllib2.Request(direct_order_url, urlencode(data))
        result = urllib2.urlopen(request).read()
        _logger.debug('result = %s', result)

        try:
            tree = objectify.fromstring(result)
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            raise

        payid = tree.get('PAYID')

        query_direct_data = dict(
            PSPID=account.ogone_pspid,
            USERID=account.ogone_userid,
            PSWD=account.ogone_password,
            ID=payid,
        )
        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % (account.ogone_env,)

        def check_status(tree, tries=2):
            # see https://secure.ogone.com/ncol/paymentinfos1.asp
            VALID_TX = [5, 9]
            WAIT_TX = [41, 50, 51, 52, 55, 56, 91, 92, 99]
            PENDING_TX = [46]   # 3DS HTML response
            # other status are errors...

            status = tree.get('STATUS')
            if status == '':
                status = None
            else:
                status = int(status)

            if status in VALID_TX:
                return True, (orderid, payid)

            if status in PENDING_TX:
                html = str(tree.HTML_ANSWER)
                values.update(ogone_3ds_html=html.decode('base64'))
                return False, (orderid, payid)

            elif status in WAIT_TX:
                time.sleep(1500)

                request = urllib2.Request(query_direct_url, urlencode(query_direct_data))
                result = urllib2.urlopen(request).read()
                _logger.debug('result = %s', result)

                try:
                    tree = objectify.fromstring(result)
                except etree.XMLSyntaxError:
                    # invalid response from ogone
                    pass   # retry...

                if tries == 0:
                    raise Exception('Cannot get transaction status...')
                return check_status(tree, tries - 1)
            else:
                error_code = tree.get('NCERROR')
                if tries and retryable(error_code):
                    return check_status(tree, tries - 1)

                error_str = tree.get('NCERRORPLUS')
                error_msg = OGONE_ERROR_MAP.get(error_code)
                error = 'ERROR: %s\n\n%s: %s' % (error_str, error_code, error_msg)
                _logger.info(error)
                raise Exception(error)

        return check_status(tree)

    def _ogone_3ds_action(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        p = self.browse(cr, uid, ids[0], context=context)
        return {
            'type': 'ir.actions.client',
            'tag': 'ogone_3ds',
            'params': {
                'payment_id': p.id,
            }
        }

    def _check_sha_sign_out(self, cr, uid, data, context=None):
        """Verify the SHA OUT signature of a ogone request.
            return the linked payment (which must be in pending mode)
        """
        payid = data['PAYID']
        orderid = data['orderID']
        p_ids = self.search(cr, uid, [('provider_ref', '=', payid), ('order_ref', '=', orderid)], context=context)
        if len(p_ids) != 1:
            raise ValidationError('Unknow order')

        payment = self.browse(cr, uid, p_ids[0], context=context)

        # if payment.state != 'pending':
        #     raise ValidationError('Invalid order')

        shasign = data['SHASIGN'].upper()

        if shasign != _generate_ogone_shasign(payment.creditcard_id.provider_account_id, 'out', data).upper():
            raise ValidationError('SHASIGN validation error')

        return payment

    def _ogone_transaction_feedback(self, cr, uid, data, context=None):
        payment = self._check_sha_sign_out(cr, uid, data, context)

        status = int(data.get('STATUS') or '0')
        if status in [5, 9]:
            payment.write(dict(state='done'))
            if payment.ogone_feedback_model and payment.ogone_feedback_eval:
                model = self.pool.get(payment.ogone_feedback_model)
                if model:
                    locals_ = {'cr': cr, 'uid': uid, 'model': model}
                    safe_eval(payment.ogone_feedback_eval, locals_)
            return True
        else:
            error_code = data.get('NCERROR')
            error_str = data.get('NCERRORPLUS')
            error_msg = OGONE_ERROR_MAP.get(error_code)
            error = 'ERROR: %s\n\n%s: %s' % (error_str, error_code, error_msg)
            _logger.info(error)
            payment.write({'state': 'error', 'error': error})
            return False
