# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging
import json
import requests
import threading
import uuid

from odoo import exceptions, _
from odoo.tools import email_normalize, exception_to_unicode

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap.odoo.com'


#----------------------------------------------------------
# Tools globals
#----------------------------------------------------------

_MAIL_PROVIDERS = {
    'gmail.com', 'hotmail.com', 'yahoo.com', 'qq.com', 'outlook.com', '163.com', 'yahoo.fr', 'live.com', 'hotmail.fr', 'icloud.com', '126.com',
    'me.com', 'free.fr', 'ymail.com', 'msn.com', 'mail.com', 'orange.fr', 'aol.com', 'wanadoo.fr', 'live.fr', 'mail.ru', 'yahoo.co.in',
    'rediffmail.com', 'hku.hk', 'googlemail.com', 'gmx.de', 'sina.com', 'skynet.be', 'laposte.net', 'yahoo.co.uk', 'yahoo.co.id', 'web.de',
    'gmail.com ', 'outlook.fr', 'telenet.be', 'yahoo.es', 'naver.com', 'hotmail.co.uk', 'gmai.com', 'foxmail.com', 'hku.hku', 'bluewin.ch',
    'sfr.fr', 'libero.it', 'mac.com', 'rocketmail.com', 'protonmail.com', 'gmx.com', 'gamil.com', 'hotmail.es', 'gmx.net', 'comcast.net',
    'yahoo.com.mx', 'linkedin.com', 'yahoo.com.br', 'yahoo.in', 'yahoo.ca', 't-online.de', '139.com', 'yandex.ru', 'yahoo.com.hk','yahoo.de',
    'yeah.net', 'yandex.com', 'nwytg.net', 'neuf.fr', 'yahoo.com.ar', 'outlook.es', 'abv.bg', 'aliyun.com', 'yahoo.com.tw', 'ukr.net', 'live.nl',
    'wp.pl', 'hotmail.it', 'live.com.mx', 'zoho.com', 'live.co.uk', 'sohu.com', 'twoomail.com', 'yahoo.com.sg', 'yahoo.com.vn',
    'windowslive.com', 'gmail', 'vols.utk.edu', 'email.com', 'tiscali.it', 'yahoo.it', 'gmx.ch', 'trbvm.com', 'nwytg.com', 'mvrht.com', 'nyit.edu',
    'o2.pl', 'live.cn', 'gmial.com', 'seznam.cz', 'live.be', 'videotron.ca', 'gmil.com', 'live.ca', 'hotmail.de', 'sbcglobal.net', 'connect.hku.hk',
    'yahoo.com.au', 'att.net', 'live.in', 'btinternet.com', 'gmx.fr', 'voila.fr', 'shaw.ca', 'prodigy.net.mx', 'vip.qq.com', 'yahoo.com.ph',
    'bigpond.com', '7thcomputing.com', 'freenet.de', 'alice.it', 'esi.dz',
    'bk.ru', 'mail.odoo.com', 'gmail.con', 'fiu.edu', 'gmal.com', 'useemlikefun.com', 'google.com', 'trbvn.com', 'yopmail.com', 'ya.ru',
    'hotmail.co.th', 'arcor.de', 'hotmail.ca', '21cn.com', 'live.de', 'outlook.de', 'gmailcom', 'unal.edu.co', 'tom.com', 'yahoo.gr',
    'gmx.at', 'inbox.lv', 'ziggo.nl', 'xs4all.nl', 'sapo.pt', 'live.com.au', 'nate.com', 'online.de', 'sina.cn', 'gmail.co', 'rogers.com',
    'mailinator.com', 'cox.net', 'hotmail.be', 'verizon.net', 'yahoo.co.jp', 'usa.com', 'consultant.com', 'hotmai.com', '189.cn',
    'sky.com', 'eezee-it.com', 'opayq.com', 'maildrop.cc', 'home.nl', 'virgilio.it', 'outlook.be', 'hanmail.net', 'uol.com.br', 'hec.ca',
    'terra.com.br', 'inbox.ru', 'tin.it', 'list.ru', 'hotmail.com ', 'safecoms.com', 'smile.fr', 'sprintit.fi', 'uniminuto.edu.co',
    'bol.com.br', 'bellsouth.net', 'nirmauni.ac.in', 'ldc.edu.in', 'ig.com.br', 'engineer.com', 'scarlet.be', 'inbox.com', 'gmaill.com',
    'freemail.hu', 'live.it', 'blackwaretech.com', 'byom.de', 'dispostable.com', 'dayrep.com', 'aim.com', 'prixgen.com', 'gmail.om',
    'asterisk-tech.mn', 'in.com', 'aliceadsl.fr', 'lycos.com', 'topnet.tn', 'teleworm.us', 'kedgebs.com', 'supinfo.com', 'posteo.de',
    'yahoo.com ', 'op.pl', 'gmail.fr', 'grr.la', 'oci.fr', 'aselcis.com', 'optusnet.com.au', 'mailcatch.com', 'rambler.ru', 'protonmail.ch',
    'prisme.ch', 'bbox.fr', 'orbitalu.com', 'netcourrier.com', 'iinet.net.au', 'cegetel.net', 'proton.me', 'dbmail.com', 'club-internet.fr', 'outlook.jp',
    'eim.ae', 'pm.me',
    # Dummy entries
    'example.com',
}
_MAIL_DOMAIN_BLACKLIST = _MAIL_PROVIDERS | {'odoo.com'}

# List of country codes for which we should offer state filtering when mining new leads.
# See crm.iap.lead.mining.request#_compute_available_state_ids() or task-2471703 for more details.
_STATES_FILTER_COUNTRIES_WHITELIST = set([
    'AR', 'AU', 'BR', 'CA', 'IN', 'MY', 'MX', 'NZ', 'AE', 'US'
])


#----------------------------------------------------------
# Tools
#----------------------------------------------------------

def mail_prepare_for_domain_search(email, min_email_length=0):
    """ Return an email address to use for a domain-based search. For generic
    email providers like gmail (see ``_MAIL_DOMAIN_BLACKLIST``) we consider
    each email as being independant (and return the whole email). Otherwise
    we return only the right-part of the email (aka "mydomain.com" if email is
    "Raoul Lachignole" <raoul@mydomain.com>).

    :param integer min_email_length: skip if email has not the sufficient minimal
      length, indicating a probably fake / wrong value (skip if 0);
    """
    if not email:
        return False
    email_tocheck = email_normalize(email, strict=False)
    if not email_tocheck:
        email_tocheck = email.casefold()

    if email_tocheck and min_email_length and len(email_tocheck) < min_email_length:
        return False

    parts = email_tocheck.rsplit('@', maxsplit=1)
    if len(parts) == 1:
        return email_tocheck
    email_domain = parts[1]
    if email_domain not in _MAIL_DOMAIN_BLACKLIST:
        return '@' + email_domain
    return email_tocheck


#----------------------------------------------------------
# Helpers for both clients and proxy
#----------------------------------------------------------

def iap_get_endpoint(env):
    url = env['ir.config_parameter'].sudo().get_param('iap.endpoint', DEFAULT_ENDPOINT)
    return url

#----------------------------------------------------------
# Helpers for clients
#----------------------------------------------------------

class InsufficientCreditError(Exception):
    pass


class IAPServerError(Exception):
    pass


def iap_jsonrpc(url, method='call', params=None, timeout=15):
    """
    Calls the provided JSON-RPC endpoint, unwraps the result and
    returns JSON-RPC errors as exceptions.
    """
    if hasattr(threading.current_thread(), 'testing') and threading.current_thread().testing:
        raise exceptions.AccessError("Unavailable during tests.")  # pylint: disable=missing-gettext

    payload = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': uuid.uuid4().hex,
    }

    _logger.info('iap jsonrpc %s', url)
    try:
        req = requests.post(url, json=payload, timeout=timeout)
        req.raise_for_status()
        response = req.json()
        _logger.info("iap jsonrpc %s responded in %.3f seconds", url, req.elapsed.total_seconds())
        if 'error' in response:
            name = response['error']['data'].get('name').rpartition('.')[-1]
            if name == 'InsufficientCreditError':
                credit_error = InsufficientCreditError(response['error']['data'].get('message'))
                credit_error.data = response['error']['data']
                raise credit_error
            else:
                raise IAPServerError("An error occurred on the IAP server")
        return response.get('result')
    except requests.exceptions.Timeout:
        _logger.warning("iap jsonrpc %s timed out", url)
        raise exceptions.AccessError(
            _('The request to the service timed out. Please contact the author of the app. The URL it tried to contact was %s', url)
        )
    except (requests.exceptions.RequestException, IAPServerError) as e:
        _logger.warning("iap jsonrpc %s failed, %s: %s", url, e.__class__.__name__, exception_to_unicode(e))
        raise exceptions.AccessError(
            _("An error occurred while reaching %s. Please contact Odoo support if this error persists.", url)
        )

#----------------------------------------------------------
# Helpers for proxy
#----------------------------------------------------------

class IapTransaction(object):

    def __init__(self):
        self.credit = None


def iap_authorize(env, key, account_token, credit, dbuuid=False, description=None, credit_template=None, ttl=4320):
    endpoint = iap_get_endpoint(env)
    params = {
        'account_token': account_token,
        'credit': credit,
        'key': key,
        'description': description,
        'ttl': ttl,
    }
    if dbuuid:
        params.update({'dbuuid': dbuuid})
    try:
        transaction_token = iap_jsonrpc(endpoint + '/iap/1/authorize', params=params)
    except InsufficientCreditError as e:
        if credit_template:
            arguments = json.loads(e.args[0])
            arguments['body'] = env['ir.qweb']._render(credit_template)
            e.args = (json.dumps(arguments),)
        raise e
    return transaction_token


def iap_cancel(env, transaction_token, key):
    endpoint = iap_get_endpoint(env)
    params = {
        'token': transaction_token,
        'key': key,
    }
    r = iap_jsonrpc(endpoint + '/iap/1/cancel', params=params)
    return r


def iap_capture(env, transaction_token, key, credit):
    endpoint = iap_get_endpoint(env)
    params = {
        'token': transaction_token,
        'key': key,
        'credit_to_capture': credit,
    }
    r = iap_jsonrpc(endpoint + '/iap/1/capture', params=params)
    return r


@contextlib.contextmanager
def iap_charge(env, key, account_token, credit, dbuuid=False, description=None, credit_template=None, ttl=4320):
    """
    Account charge context manager: takes a hold for ``credit``
    amount before executing the body, then captures it if there
    is no error, or cancels it if the body generates an exception.

    :param str key: service identifier
    :param str account_token: user identifier
    :param int credit: cost of the body's operation
    :param description: a description of the purpose of the charge,
                        the user will be able to see it in their
                        dashboard
    :type description: str
    :param credit_template: a QWeb template to render and show to the
                            user if their account does not have enough
                            credits for the requested operation
    :param int ttl: transaction time to live in hours.
                    If the credit are not captured when the transaction
                    expires, the transaction is canceled
    :type credit_template: str
    """
    transaction_token = iap_authorize(env, key, account_token, credit, dbuuid, description, credit_template, ttl)
    try:
        transaction = IapTransaction()
        transaction.credit = credit
        yield transaction
    except Exception as e:
        r = iap_cancel(env,transaction_token, key)
        raise e
    else:
        r = iap_capture(env,transaction_token, key, transaction.credit)
