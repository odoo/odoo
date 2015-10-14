# -*- coding: utf-'8' "-*-"

import logging
from lxml import etree, objectify
import time
from unicodedata import normalize
from urllib import urlencode
import urllib2

from openerp.osv import osv

_logger = logging.getLogger(__name__)


class PaymentMethod(osv.Model):
    _inherit = 'payment.method'

    def ogone_create(self, cr, uid, values, context=None):
        if values.get('cc_number'):
            # create a alias via batch
            values['cc_number'] = values['cc_number'].replace(' ', '')
            acquirer = self.pool['payment.acquirer'].browse(cr, uid, values['acquirer_id'])
            alias = 'ODOO-NEW-ALIAS-%s' % time.time()

            expiry = str(values['cc_expiry'][:2]) + str(values['cc_expiry'][-2:])
            line = 'ADDALIAS;%(alias)s;%(cc_holder_name)s;%(cc_number)s;%(expiry)s;%(cc_brand)s;%(pspid)s'
            line = line % dict(values, alias=alias, expiry=expiry, pspid=acquirer.ogone_pspid)

            data = {
                'FILE_REFERENCE': alias,
                'TRANSACTION_CODE': 'ATR',
                'OPERATION': 'SAL',
                'NB_PAYMENTS': 1,   # even if we do not actually have any payment, ogone want it to not be 0
                'FILE': normalize('NFKD', line).encode('ascii','ignore'),  # Ogone Batch must be ASCII only
                'REPLY_TYPE': 'XML',
                'PSPID': acquirer.ogone_pspid,
                'USERID': acquirer.ogone_userid,
                'PSWD': acquirer.ogone_password,
                'PROCESS_MODE': 'CHECKANDPROCESS',
            }

            url = 'https://secure.ogone.com/ncol/%s/AFU_agree.asp' % (acquirer.environment,)
            request = urllib2.Request(url, urlencode(data))

            result = urllib2.urlopen(request).read()

            try:
                tree = objectify.fromstring(result)
            except etree.XMLSyntaxError:
                _logger.exception('Invalid xml response from ogone')
                return None

            error_code = error_str = None
            if hasattr(tree, 'PARAMS_ERROR'):
                error_code = tree.NCERROR.text
                error_str = 'PARAMS ERROR: %s' % (tree.PARAMS_ERROR.text or '',)
            else:
                node = tree.FORMAT_CHECK
                error_node = getattr(node, 'FORMAT_CHECK_ERROR', None)
                if error_node is not None:
                    error_code = error_node.NCERROR.text
                    error_str = 'CHECK ERROR: %s' % (error_node.ERROR.text or '',)

            if error_code:
                error_msg = tree.get(error_code)
                error = '%s\n\n%s: %s' % (error_str, error_code, error_msg)
                _logger.error(error)
                raise Exception(error)

            return {
                'acquirer_ref': alias,
                'name': 'XXXXXXXXXXXX%s - %s' % (values['cc_number'][-4:], values['cc_holder_name'])
            }
        return {}
