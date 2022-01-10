# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import struct
import zipfile
from base64 import b64encode
from re import sub as regex_sub

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree
from odoo import models
from odoo.tools import get_lang
from OpenSSL.crypto import FILETYPE_PEM, load_certificate, load_privatekey
from urllib3.util.ssl_ import DEFAULT_CIPHERS, create_urllib3_context

# -------------------------------------------------------------------------
# HTTPS REQUESTS
# -------------------------------------------------------------------------

EUSKADI_CIPHERS = f"{DEFAULT_CIPHERS}:!DH"

# Custom adapter to perform HTTP requests using
class PatchedHTTPAdapter(requests.adapters.HTTPAdapter):
    """ An adapter to block DH ciphers which may not work for the tax agencies called"""

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
class L10nEsTbaiFillSignXml(models.AbstractModel):
    _name = 'l10n_es.edi.tbai.util'
    _description = "Utility Methods for Bask Country's TicketBAI"

    # -------------------------------------------------------------------------
    # XML: FILL & SIGN
    # -------------------------------------------------------------------------

    NS_MAP = {"ds": "http://www.w3.org/2000/09/xmldsig#"}

    def post(self, *args, **kwargs):
        session = requests.Session()
        session.cert = kwargs.pop('pkcs12_data')
        session.mount("https://", PatchedHTTPAdapter())
        return session.request('post', *args, **kwargs)

    def get_response_values(self, xml_res):
        tbai_id_node = xml_res.find(r'.//IdentificadorTBAI')
        tbai_id = '' if tbai_id_node is None else tbai_id_node.text
        messages = ''
        node_name = 'Azalpena' if get_lang(self.env).code == 'eu_ES' else 'Descripcion'
        for xml_res_node in xml_res.findall(r'.//ResultadosValidacion'):
            messages += xml_res_node.find('Codigo').text + ": " + xml_res_node.find(node_name).text + "\n"
        return messages, tbai_id

    def zip_files(self, files, fnames, stream):
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for file, fname in zip(files, fnames):
                fname = regex_sub("/", "_", fname)  # slashes create directory structure
                zipf.writestr(fname, file)
        return stream

    def base64_print(self, string):
        string = str(string, "utf8")
        return "\n".join(
            string[pos: pos + 64]  # noqa: E203
            for pos in range(0, len(string), 64)
        )

    def get_uri(self, uri, reference):
        node = reference.getroottree()
        if uri == "":
            return etree.tostring(
                node,
                method="c14n",
                with_comments=False,
                exclusive=False,
            )

        if uri.startswith("#"):
            query = "//*[@*[local-name() = '{}' ]=$uri]"
            results = []
            for id in ("ID", "Id", "id"):
                results = node.xpath(query.format(id), uri=uri.lstrip("#"))
                if len(results) == 1:
                    return etree.tostring(
                        results[0],
                        method="c14n",
                        with_comments=False,
                        exclusive=False,
                    )
                if len(results) > 1:
                    raise Exception("Ambiguous reference URI {} resolved to {} nodes".format(
                        uri, len(results)))

        raise Exception('URI "' + uri + '" cannot be read')

    def reference_digests(self, node):
        for reference in node.findall("ds:Reference", namespaces=self.NS_MAP):
            ref_node = self.get_uri(reference.get("URI", ""), reference)
            lib = hashlib.new("sha256")
            lib.update(ref_node)
            reference.find("ds:DigestValue", namespaces=self.NS_MAP).text = b64encode(lib.digest())

    def long_to_bytes(self, n, blocksize=0):
        """
        Convert a long integer to a byte string.
        If optional blocksize is given and greater than zero, pad the front of the
        byte string with binary zeros so that the length is a multiple of
        blocksize.
        """
        # convert to byte string
        s = b""
        pack = struct.pack
        while n > 0:
            s = pack(b">I", n & 0xFFFFFFFF) + s
            n = n >> 32
        # strip off leading zeros
        for i in range(len(s)):
            if s[i] != b"\000"[0]:
                break
        else:
            # only happens when n == 0
            s = b"\000"
            i = 0
        s = s[i:]
        # padding
        if blocksize > 0 and len(s) % blocksize:
            s = (blocksize - len(s) % blocksize) * b"\000" + s
        return s

    def fill_signature(self, node, private_key):
        signed_info_xml = node.find("ds:SignedInfo", namespaces=self.NS_MAP)

        signed_info = etree.tostring(
            signed_info_xml,
            method="c14n",
            with_comments=False,
            exclusive=False,
        )

        signature = private_key.sign(
            signed_info,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        node.find("ds:SignatureValue", namespaces=self.NS_MAP).text = self.base64_print(b64encode(signature))

    # -------------------------------------------------------------------------
    # CRC-8
    # -------------------------------------------------------------------------

    CRC8_TABLE = [
        0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15, 0x38, 0x3F, 0x36, 0x31, 0x24, 0x23, 0x2A, 0x2D,
        0x70, 0x77, 0x7E, 0x79, 0x6C, 0x6B, 0x62, 0x65, 0x48, 0x4F, 0x46, 0x41, 0x54, 0x53, 0x5A, 0x5D,
        0xE0, 0xE7, 0xEE, 0xE9, 0xFC, 0xFB, 0xF2, 0xF5, 0xD8, 0xDF, 0xD6, 0xD1, 0xC4, 0xC3, 0xCA, 0xCD,
        0x90, 0x97, 0x9E, 0x99, 0x8C, 0x8B, 0x82, 0x85, 0xA8, 0xAF, 0xA6, 0xA1, 0xB4, 0xB3, 0xBA, 0xBD,
        0xC7, 0xC0, 0xC9, 0xCE, 0xDB, 0xDC, 0xD5, 0xD2, 0xFF, 0xF8, 0xF1, 0xF6, 0xE3, 0xE4, 0xED, 0xEA,
        0xB7, 0xB0, 0xB9, 0xBE, 0xAB, 0xAC, 0xA5, 0xA2, 0x8F, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9D, 0x9A,
        0x27, 0x20, 0x29, 0x2E, 0x3B, 0x3C, 0x35, 0x32, 0x1F, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0D, 0x0A,
        0x57, 0x50, 0x59, 0x5E, 0x4B, 0x4C, 0x45, 0x42, 0x6F, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7D, 0x7A,
        0x89, 0x8E, 0x87, 0x80, 0x95, 0x92, 0x9B, 0x9C, 0xB1, 0xB6, 0xBF, 0xB8, 0xAD, 0xAA, 0xA3, 0xA4,
        0xF9, 0xFE, 0xF7, 0xF0, 0xE5, 0xE2, 0xEB, 0xEC, 0xC1, 0xC6, 0xCF, 0xC8, 0xDD, 0xDA, 0xD3, 0xD4,
        0x69, 0x6E, 0x67, 0x60, 0x75, 0x72, 0x7B, 0x7C, 0x51, 0x56, 0x5F, 0x58, 0x4D, 0x4A, 0x43, 0x44,
        0x19, 0x1E, 0x17, 0x10, 0x05, 0x02, 0x0B, 0x0C, 0x21, 0x26, 0x2F, 0x28, 0x3D, 0x3A, 0x33, 0x34,
        0x4E, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5C, 0x5B, 0x76, 0x71, 0x78, 0x7F, 0x6A, 0x6D, 0x64, 0x63,
        0x3E, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2C, 0x2B, 0x06, 0x01, 0x08, 0x0F, 0x1A, 0x1D, 0x14, 0x13,
        0xAE, 0xA9, 0xA0, 0xA7, 0xB2, 0xB5, 0xBC, 0xBB, 0x96, 0x91, 0x98, 0x9F, 0x8A, 0x8D, 0x84, 0x83,
        0xDE, 0xD9, 0xD0, 0xD7, 0xC2, 0xC5, 0xCC, 0xCB, 0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3
    ]

    def crc8(self, data):
        crc = 0x0
        for c in data:
            crc = self.CRC8_TABLE[(crc ^ ord(c)) & 0xFF]
        return '{:03d}'.format(crc & 0xFF)
