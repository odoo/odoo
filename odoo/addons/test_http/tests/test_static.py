# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from os.path import basename, join as opj
from unittest.mock import patch
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import config, file_open

from .test_common import TestHttpBase


@tagged('post_install', '-at_install')
class TestHttpStaticCommon(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(config, 'options', {**config.options, 'x_sendfile': False})

        with file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
            cls.gizeh_data = file.read()

        with file_open('web/static/img/placeholder.png', 'rb') as file:
            cls.placeholder_data = file.read()

    def assertDownload(
        self, url, headers, assert_status_code, assert_headers, assert_content=None
    ):
        res = self.db_url_open(url, headers=headers)
        res.raise_for_status()
        self.assertEqual(res.status_code, assert_status_code)
        for header_name, header_value in assert_headers.items():
            self.assertEqual(res.headers.get(header_name), header_value)
        if assert_content:
            self.assertEqual(res.content, assert_content)
        return res

    def assertDownloadGizeh(self, url, x_sendfile=None, assert_filename='gizeh.png'):
        headers = {
            'Content-Length': '814',
            'Content-Type': 'image/png',
            'Content-Disposition': f'inline; filename={assert_filename}'
        }

        if x_sendfile:
            sha = basename(x_sendfile)
            headers['X-Sendfile'] = x_sendfile
            headers['X-Accel-Redirect'] = f'/web/filestore/{self.cr.dbname}/{sha[:2]}/{sha}'
            headers['Content-Length'] = '0'

        return self.assertDownload(url, {}, 200, headers, b'' if x_sendfile else self.gizeh_data)

    def assertDownloadPlaceholder(self, url):
        headers = {
            'Content-Length': '6078',
            'Content-Type': 'image/png',
            'Content-Disposition': 'inline; filename=placeholder.png'
        }
        return self.assertDownload(url, {}, 200, headers, self.placeholder_data)


@tagged('post_install', '-at_install')
class TestHttpStatic(TestHttpStaticCommon):
    def test_static00_static(self):
        with self.subTest(x_sendfile=False):
            res = self.assertDownloadGizeh('/test_http/static/src/img/gizeh.png')
            self.assertEqual(res.headers.get('Cache-Control', ''), 'public, max-age=604800')

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            # The file is outside of the filestore, X-Sendfile disabled
            res = self.assertDownloadGizeh('/test_http/static/src/img/gizeh.png', x_sendfile=False)
            self.assertEqual(res.headers.get('Cache-Control', ''), 'public, max-age=604800')

    def test_static01_debug_assets(self):
        session = self.authenticate(None, None)
        session.debug = 'assets'

        res = self.assertDownloadGizeh('/test_http/static/src/img/gizeh.png')
        self.assertEqual(res.headers.get('Cache-Control', ''), 'no-cache, max-age=0')

    def test_static02_not_found(self):
        res = self.nodb_url_open("/test_http/static/i-dont-exist")
        self.assertEqual(res.status_code, 404)

    def test_static03_attachment_fallback(self):
        attachment = self.env.ref('test_http.gizeh_png')

        with self.subTest(x_sendfile=False):
            self.assertDownloadGizeh(attachment.url)

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            self.assertDownloadGizeh(
                attachment.url,
                x_sendfile=opj(config.filestore(self.env.cr.dbname), attachment.store_fname),
            )

    def test_static04_web_content(self):
        attachment = self.env.ref('test_http.gizeh_png')

        with self.subTest(x_sendfile=False):
            self.assertDownloadGizeh('/web/content/test_http.gizeh_png')

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            self.assertDownloadGizeh(
                '/web/content/test_http.gizeh_png',
                x_sendfile=opj(config.filestore(self.env.cr.dbname), attachment.store_fname),
            )

    def test_static05_web_image(self):
        attachment = self.env.ref('test_http.gizeh_png')

        with self.subTest(x_sendfile=False):
            self.assertDownloadGizeh('/web/image/test_http.gizeh_png')

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            self.assertDownloadGizeh(
                '/web/image/test_http.gizeh_png',
                x_sendfile=opj(config.filestore(self.env.cr.dbname), attachment.store_fname),
            )

    def test_static06_attachment_internal_url(self):
        with self.subTest(x_sendfile=False):
            self.assertDownloadGizeh('/web/image/test_http.gizeh_url')

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            # The file is outside of the filestore, X-Sendfile disabled
            self.assertDownloadGizeh('/web/image/test_http.gizeh_url', x_sendfile=False)

    def test_static07_attachment_external_url(self):
        res = self.db_url_open('/web/content/test_http.rickroll')
        res.raise_for_status()
        self.assertEqual(res.status_code, 301)
        self.assertEqual(res.headers.get('Location'), 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')

    def test_static08_binary_field_attach(self):
        earth = self.env.ref('test_http.earth')
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'test_http.stargate'),
            ('res_id', '=', earth.id),
            ('res_field', '=', 'glyph_attach')
        ], limit=1)
        attachment_path = opj(config.filestore(self.env.cr.dbname), attachment.store_fname)

        with self.subTest(x_sendfile=False):
            self.assertDownloadGizeh(
                f'/web/content/test_http.stargate/{earth.id}/glyph_attach',
                assert_filename='Earth.png'
            )

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            self.assertDownloadGizeh(
                f'/web/content/test_http.stargate/{earth.id}/glyph_attach',
                x_sendfile=attachment_path,
                assert_filename='Earth.png'
            )

    def test_static09_binary_field_inline(self):
        self.assertDownloadGizeh(
            '/web/content/test_http.earth?field=glyph_inline',
            assert_filename='Earth.png'
        )

    def test_static10_filename(self):
        with self.subTest("record name"):
            self.assertDownloadGizeh(
                '/web/content/test_http.gizeh_png',
                assert_filename='gizeh.png',
            )

        with self.subTest("forced name"):
            self.assertDownloadGizeh(
                '/web/content/test_http.gizeh_png?filename=pyramid.png',
                assert_filename='pyramid.png',
            )

        with self.subTest("filename field"):
            self.assertDownloadGizeh(
                '/web/content/test_http.earth?field=glyph_inline&filename_field=address',
                assert_filename='sq5Abt.png',
            )

    def test_static11_bad_filenames(self):
        with self.subTest("missing record name"):
            gizeh = self.env.ref('test_http.gizeh_png')
            realname = gizeh.name
            gizeh.name = ''
            try:
                self.assertDownloadGizeh(
                    '/web/content/test_http.gizeh_png',
                    assert_filename=f'ir_attachment-{gizeh.id}-raw.png'
                )
            finally:
                gizeh.name = realname

        with self.subTest("missing file extension"):
            self.assertDownloadGizeh(
                '/web/content/test_http.gizeh_png?filename=pyramid',
                assert_filename='pyramid.png',
            )

        with self.subTest("wrong file extension"):
            res = self.assertDownloadGizeh(
                '/web/content/test_http.gizeh_png?filename=pyramid.jpg',
                assert_filename='pyramid.jpg',
            )
            self.assertEqual(res.headers['Content-Type'], 'image/png')

        with self.subTest("dotted name"):
            res = self.assertDownloadGizeh(
                '/web/content/test_http.gizeh_png?filename=pyramid.of.gizeh',
                assert_filename='pyramid.of.gizeh.png',
            )

    def test_static12_not_found_to_placeholder(self):
        with self.subTest(x_sendfile=False):
            self.assertDownloadPlaceholder('/web/image/idontexist')

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            # The file is outside of the filestore, X-Sendfile disabled
            self.assertDownloadPlaceholder('/web/image/idontexist')

    def test_static13_empty_to_placeholder(self):
        att = self.env['ir.attachment'].create([{
            'name': 'empty.png',
            'type': 'binary',
            'raw': b'',  # this is not a valid png file, whatever
            'public': True
        }])

        with self.subTest(x_sendfile=False):
            self.assertDownloadPlaceholder(f'/web/image/{att.id}')

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            # The file is outside of the filestore, X-Sendfile disabled
            self.assertDownloadPlaceholder(f'/web/image/{att.id}')


    def test_static14_download_not_found(self):
        res = self.url_open('/web/image/idontexist?download=True')
        self.assertEqual(res.status_code, 404)

    def test_static15_range(self):
        self.assertDownload(
            url='/web/content/test_http.gizeh_png',
            headers={'Range': 'bytes=100-199'},

            assert_status_code=206,
            assert_headers={
                'Content-Length': '100',
                'Content-Range': 'bytes 100-199/814',
                'Content-Type': 'image/png',
                'Content-Disposition': 'inline; filename=gizeh.png',
            },
            assert_content=self.gizeh_data[100:200]
        )


class TestHttpStaticCache(TestHttpStaticCommon):
    @freeze_time(datetime.utcnow())
    def test_static_cache0_standard(self, domain=''):
        # Wed, 21 Oct 2015 07:28:00 GMT
        # The timezone should be %Z (instead of 'GMT' hardcoded) but
        # somehow strftime doesn't set it.
        http_date_format = '%a, %d %b %Y %H:%M:%S GMT'
        one_week_away = (datetime.utcnow() + timedelta(weeks=1)).strftime(http_date_format)

        res1 = self.nodb_url_open(f'{domain}/test_http/static/src/img/gizeh.png')
        res1.raise_for_status()
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.headers.get('Cache-Control'), 'public, max-age=604800')  # one week
        self.assertEqual(res1.headers.get('Expires'), one_week_away)
        self.assertIn('ETag', res1.headers)

        res2 = self.nodb_url_open(f'{domain}/test_http/static/src/img/gizeh.png', headers={
            'If-None-Match': res1.headers['ETag']
        })
        res2.raise_for_status()
        self.assertEqual(res2.status_code, 304, "We should not download the file again.")

    @freeze_time(datetime.utcnow())
    def test_static_cache1_unique(self, domain=''):
        # Wed, 21 Oct 2015 07:28:00 GMT
        # The timezone should be %Z (instead of 'GMT' hardcoded) but
        # somehow strftime doesn't set it.
        http_date_format = '%a, %d %b %Y %H:%M:%S GMT'
        one_year_away = (datetime.utcnow() + timedelta(days=365)).strftime(http_date_format)

        res1 = self.assertDownloadGizeh(f'{domain}/web/content/test_http.gizeh_png?unique=1')
        self.assertEqual(res1.headers.get('Cache-Control'), 'public, max-age=31536000')  # one year
        self.assertEqual(res1.headers.get('Expires'), one_year_away)
        self.assertIn('ETag', res1.headers)

        res2 = self.db_url_open(f'{domain}/web/content/test_http.gizeh_png?unique=1', headers={
            'If-None-Match': res1.headers['ETag']
        })
        res2.raise_for_status()
        self.assertEqual(res2.status_code, 304, "We should not download the file again.")

    @freeze_time(datetime.utcnow())
    def test_static_cache2_nocache(self, domain=''):
        res1 = self.assertDownloadGizeh(f'{domain}/web/content/test_http.gizeh_png?nocache=1')
        self.assertEqual(res1.headers.get('Cache-Control'), 'no-cache')
        self.assertNotIn('Expires', res1.headers)
        self.assertIn('ETag', res1.headers)

        res2 = self.db_url_open(f'{domain}/web/content/test_http.gizeh_png?nocache=1', headers={
            'If-None-Match': res1.headers['ETag']
        })
        res2.raise_for_status()
        self.assertEqual(res2.status_code, 304, "We should not download the file again.")
