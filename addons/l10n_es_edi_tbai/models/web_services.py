# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from odoo.tools import get_lang
from OpenSSL.crypto import FILETYPE_PEM, load_certificate, load_privatekey
from urllib3.util.ssl_ import DEFAULT_CIPHERS, create_urllib3_context

# -------------------------------------------------------------------------
# TICKETBAI WEB SERVICES
# -------------------------------------------------------------------------

class TicketBaiWebServices():
    """Provides helper methods for interacting with the Bask country's TicketBai servers."""

    def _post(self, *args, **kwargs):
        session = requests.Session()
        session.cert = kwargs.pop('pkcs12_data')
        session.mount("https://", PatchedHTTPAdapter())
        return session.request('post', *args, **kwargs)

    def _get_response_values(self, xml_res, env):
        tbai_id_node = xml_res.find(r'.//IdentificadorTBAI')
        tbai_id = '' if tbai_id_node is None else tbai_id_node.text
        messages = ''
        already_received = False
        node_name = 'Azalpena' if get_lang(env).code == 'eu_ES' else 'Descripcion'
        for xml_res_node in xml_res.findall(r'.//ResultadosValidacion'):
            message_code = xml_res_node.find('Codigo').text
            messages += message_code + ": " + xml_res_node.find(node_name).text + "\n"
            if message_code in ('005', '019'):
                already_received = True  # error codes 5/19 mean XML was already received with that sequence
        return messages, already_received, tbai_id


# -------------------------------------------------------------------------
# HTTPS ADAPTER
# -------------------------------------------------------------------------

EUSKADI_CIPHERS = f"{DEFAULT_CIPHERS}:!DH"

# Custom adapter to perform HTTP requests using
class PatchedHTTPAdapter(requests.adapters.HTTPAdapter):
    """An adapter to block DH ciphers which may not work for the tax agencies called."""

    def init_poolmanager(self, *args, **kwargs):
        # OVERRIDE
        kwargs['ssl_context'] = create_urllib3_context(ciphers=EUSKADI_CIPHERS)
        return super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        # OVERRIDE
        # The last parameter is only used by the super method to check if the file exists.
        # In our case, cert is an odoo record 'l10n_es_edi_tbai.certificate' so not a path to a file.
        # By putting 'None' as last parameter, we ensure the check about TLS configuration is
        # still made without checking temporary files exist.
        super().cert_verify(conn, url, verify, None)
        conn.cert_file = cert
        conn.key_file = None

    def get_connection(self, url, proxies=None):
        # OVERRIDE
        # Patch the OpenSSLContext to decode the certificate in-memory.
        conn = super().get_connection(url, proxies=proxies)
        context = conn.conn_kw['ssl_context']

        def patched_load_cert_chain(l10n_es_odoo_certificate, keyfile=None, password=None):
            cert_file, key_file, dummy = l10n_es_odoo_certificate._decode_certificate()
            cert_obj = load_certificate(FILETYPE_PEM, cert_file)
            pkey_obj = load_privatekey(FILETYPE_PEM, key_file)

            context._ctx.use_certificate(cert_obj)
            context._ctx.use_privatekey(pkey_obj)

        context.load_cert_chain = patched_load_cert_chain

        return conn
