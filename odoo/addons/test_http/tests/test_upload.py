# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import socket
import typing
from collections.abc import Collection, Mapping
from email import message_from_bytes
from email.policy import HTTP as POLICY_HTTP
from http import HTTPStatus
from io import FileIO
from os.path import basename
from urllib.parse import quote, urlsplit

from odoo.fields import Command
from odoo.tests import Like, RecordCapturer
from odoo.tools import file_open, frozendict

from .test_static import TestHttpStaticCommon

if typing.TYPE_CHECKING:
    from email.message import EmailMessage

_BOUNDARY = b"596f7520666f756e64206d6521203a44"
POST_MULTIPART = b"""\
POST %%(url)s HTTP/1.1\r
Host: %%(base_url)s\r
User-Agent: Odoo\r
Connection: close\r
Cookie: session_id=%%(sid)s; test_request_key=%%(test_request_key)s\r
Content-Length: %%(content_length)d\r
Content-Type: multipart/form-data; boundary=%s\r
\r
""" % _BOUNDARY


class Part(typing.NamedTuple):
    name: bytes
    content: bytes
    filename: bytes | None = None
    content_type: bytes | None = None

    def pack(self):
        part = bytearray(b"Content-Disposition: form-data")
        part += b'; name="%s"' % self.name.replace(b'"', b'\\"')
        if self.filename is not None:
            part += b"; filename*=%s" % self.filename
        part += b"\r\n"
        if self.content_type is not None:
            part += b"Content-Type: %s\r\n" % self.content_type
        part += b"\r\n"
        part += self.content
        return part


def make_mutli_part(*parts):
    return b''.join([
         b"--%s\r\n%s\r\n" % (_BOUNDARY, p.pack()) for p in parts
    ]) + b'--%s--\r\n' % _BOUNDARY


def content_disposition_filename(filename: str, encoding='utf-8') -> bytes:
    return f"{encoding}''{quote(filename, safe='', encoding=encoding)}".encode('ascii')


class TestHttpUpload(TestHttpStaticCommon):
    def make_upload_request(
        self,
        url: str,
        data: Mapping[str, str] = frozendict(),
        files: Mapping[str, FileIO] = frozendict(),
        parts: Collection[Part] = (),
    ) -> tuple[HTTPStatus, 'EmailMessage']:
        """ Forge and send a multipart POST request. """
        if data or files:
            parts = list(parts) + [
                Part(name=name.encode('ascii'), content=str(value).encode('ascii'))
                for name, value in data.items()
            ] + [
                Part(
                    name=name.encode('ascii'),
                    content=file.read(),
                    filename=content_disposition_filename(basename(file.name)),
                ) for name, file in files.items()
            ]

        body = make_mutli_part(*parts)
        assert body.count(_BOUNDARY) == len(parts) + 1, \
            "{{_BOUNDARY}} must not appear inside the data"

        with self.allow_requests():
            u = urlsplit(self.base_url())
            head = POST_MULTIPART % {
                b'url': url.encode('ascii'),
                b'base_url': u.netloc.encode('ascii'),
                b'sid': self.opener.cookies['session_id'].encode('ascii'),
                b'test_request_key': self.opener.cookies['test_request_key'].encode('ascii'),
                b'content_length': len(body),
            }
            with socket.create_connection((u.hostname, u.port), timeout=1) as sock:
                sock.send(head)
                sock.send(body)
                sock.shutdown(socket.SHUT_WR)
                res = bytearray()
                while chunk := sock.recv(16384):
                    res += chunk

        http_line, new_line, head_body = res.partition(b'\r\n')
        if not new_line:
            raise ValueError
        _version, status, _reason = http_line.split(b' ', 2)

        return HTTPStatus(int(status)), message_from_bytes(head_body, policy=POLICY_HTTP)

    def test_http_make_upload_request(self):
        # Test no weird stuff, just make sure make_upload_request works
        self.authenticate('admin', 'admin')
        with (file_open('base/tests/files/file.xml', 'rb') as xml_file,
              RecordCapturer(self.env['ir.attachment']) as record_capture):
            xml_data = xml_file.read()
            xml_file.seek(0)
            status, message = self.make_upload_request(
                '/web/upload',
                data={'public': '1'},
                files={'file': xml_file},
                parts=(
                    Part(b'mimetype', b'text/plain', content_type=b'text/plain'),
                ),
            )

        attach, = record_capture.records
        self.assertEqual(attach.name, 'file.xml')
        self.assertEqual(attach.raw.content, xml_data)
        self.assertEqual(attach.mimetype, 'text/plain')
        self.assertEqual(attach.file_size, 624)
        self.assertEqual(attach.checksum, '97ed52228d20bc5483de93063e4b650add68e296')
        self.assertEqual(attach.public, True)

        self.assertEqual(status, HTTPStatus.CREATED, message)
        self.assertEqual(message['Location'], f'/web/content/{attach.id}')
        self.assertIn("<p>You should be redirected automatically", message.get_content())

    def test_http_upload(self):
        self.authenticate('demo', 'demo')
        with (file_open('test_http/static/src/img/gizeh.png', 'rb') as gizeh_file,
              RecordCapturer(self.env['ir.attachment']) as record_capture):
            res = self.db_url_open('/web/upload', files={'file': gizeh_file}, data={'plop': 'machin'})
        res.raise_for_status()

        attach, = record_capture.records
        self.assertEqual(attach.name, 'gizeh.png')
        self.assertEqual(attach.raw.content, self.gizeh_data)
        self.assertEqual(attach.mimetype, 'image/png')
        self.assertEqual(attach.file_size, 814)
        self.assertEqual(attach.checksum, '0126381835cceaf2d113bdbbcb4d7851dcc1c721')
        self.assertEqual(attach.public, False)

        self.assertEqual(res.status_code, HTTPStatus.CREATED)
        self.assertEqual(res.headers['Location'], f'/web/content/{attach.id}')
        self.assertDownloadGizeh(res.headers['Location'])

    def test_http_upload_no_access(self):
        user_portal = self.env['res.users'].search([('login', '=', 'portal')])
        if not user_portal:
            self.env['ir.config_parameter'].sudo().set_int('auth_password_policy.minlength', 7)
            partner_portal = self.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
                'tz': 'UTC',
            })
            user_portal = self.env['res.users'].create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': partner_portal.id,
                'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
            })

        self.authenticate(None, None)
        with file_open('test_http/static/src/img/gizeh.png', 'rb') as gizeh_file:
            res = self.db_url_open('/web/upload', files={'file': gizeh_file})
        self.assertEqual(res.status_code, HTTPStatus.SEE_OTHER)
        self.assertURLEqual(res.headers.get('Location', ''), '/web/login?redirect=/web/upload?')

        self.authenticate('portal', 'portal')
        with (file_open('test_http/static/src/img/gizeh.png', 'rb') as gizeh_file,
              self.assertLogs('odoo.http', logging.WARNING) as log_capture):
            res = self.db_url_open('/web/upload', files={'file': gizeh_file})
        self.assertEqual(res.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(log_capture.output, [
            Like("WARNING:odoo.http:You are not allowed to create 'Attachment'..."),
        ])
