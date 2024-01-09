# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime, timedelta
from http import HTTPStatus
from os.path import basename, join as opj
from unittest.mock import patch
from freezegun import freeze_time

import odoo
from odoo.tests import new_test_user, tagged, RecordCapturer
from odoo.tools import config, file_open, image_process

from .test_common import TestHttpBase


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

    def test_static16_public_access_rights(self):
        default_user = self.env.ref('base.default_user')

        with self.subTest('model access rights'):
            res = self.url_open(f'/web/content/res.users/{default_user.id}/image_128')
            self.assertEqual(res.status_code, 404)

        with self.subTest('attachment + field access rights'):
            res = self.url_open('/web/content/test_http.pegasus?field=picture')
            self.assertEqual(res.status_code, 404)

        with self.subTest('related attachment + field access rights'):
            res = self.url_open('/web/content/test_http.earth?field=galaxy_picture')
            self.assertEqual(res.status_code, 404)

    def test_static17_content_missing_checksum(self):
        att = self.env['ir.attachment'].create({
            'name': 'testhttp.txt',
            'db_datas': 'some data',
            'public': True,
        })
        self.assertFalse(att.checksum)
        self.assertDownload(
            url=f'/web/content/{att.id}',
            headers={},

            assert_status_code=200,
            assert_headers={
                'Content-Length': '9',
                'Content-Type': 'text/plain; charset=utf-8',
                'Content-Disposition': 'inline; filename=testhttp.txt',
            },
            assert_content=b'some data',
        )

    def test_static18_image_missing_checksum(self):
        with file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
            att = self.env['ir.attachment'].create({
                'name': 'gizeh.png',
                'db_datas': file.read(),
                'mimetype': 'image/png',
                'public': True,
            })
        self.assertFalse(att.checksum)
        self.assertDownloadGizeh(f'/web/image/{att.id}')


@tagged('post_install', '-at_install')
class TestHttpStaticLogo(TestHttpStaticCommon):
    @staticmethod
    def img_data_to_web_data(img_base_64):
        return image_process(img_base_64, size=(180, 0))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ResCompany = cls.env['res.company']
        cls.default_logo_data = cls.img_data_to_web_data(base64.b64decode(ResCompany._get_logo()))
        cls.gizeh_data_b64 = base64.encodebytes(cls.gizeh_data)
        cls.logo_gizeh_data = cls.img_data_to_web_data(cls.gizeh_data)
        with file_open('web/static/img/nologo.png', 'rb') as file:
            cls.logo_no_logo_data = file.read()
        cls.headers_default_logo = {
            'Content-Length': f'{len(cls.default_logo_data)}',
            'Content-Type': 'image/png',
            'Content-Disposition': 'inline; filename=logo.png'
        }
        cls.headers_logo_gizeh = {
            'Content-Length': f'{len(cls.logo_gizeh_data)}',
            'Content-Type': 'image/png',
            'Content-Disposition': 'inline; filename=logo.png'
        }
        cls.headers_logo_no_logo = {
            'Content-Length': f'{len(cls.logo_no_logo_data)}',
            'Content-Type': 'image/png',
            'Content-Disposition': 'inline; filename=nologo.png'
        }
        super_user = cls.env['res.users'].browse([odoo.SUPERUSER_ID])
        companies = ResCompany.browse([super_user.company_id.id]) | ResCompany.create(
            {
                'name': 'Company 2',
                'email': 'company.2@test.example.com',
                'country_id': cls.env.ref('base.fr').id,
            }
        )
        cls.company_of_superuser, cls.company2 = companies
        cls.password = 'Pl1bhD@2!kXZ'
        cls.user_of_company_of_superuser, cls.user_company2 = [
            new_test_user(cls.env, f'user_{company.id}', company_id=company.id, password=cls.password)
            for company in companies]

    def assertDownloadLogo(self, assert_headers, assert_content, user=None, company=None):
        """Assert that the logo endpoint returns the right image and headers.

        :param dict assert_headers: expected headers
        :param bytes assert_content: expected image data
        :param user: optional user, if set the check will be done while being authenticated with that user
        :param company: optional company, if set the company will be appended in the URL parameters
        """
        url_suffix = f'?company={company.id}' if company else ''
        if user:
            self.authenticate(user.login, self.password)
        else:
            self.authenticate(None, None)
        self.assertDownload(f'/logo.png{url_suffix}', {},
                            assert_status_code=200, assert_headers=assert_headers, assert_content=assert_content)

    def assertDownloadLogoDefault(self, user=None, company=None):
        self.assertDownloadLogo(self.headers_default_logo, self.default_logo_data, user, company)

    def assertDownloadLogoGizeh(self, user=None, company=None):
        self.assertDownloadLogo(self.headers_logo_gizeh, self.logo_gizeh_data, user, company)

    def assertDownloadLogoNoLogo(self, user=None, company=None):
        self.assertDownloadLogo(self.headers_logo_no_logo, self.logo_no_logo_data, user, company)

    def test_default_logo(self):
        self.assertDownloadLogoDefault()
        self.assertDownloadLogoDefault(company=self.company_of_superuser)
        self.assertDownloadLogoDefault(user=self.user_of_company_of_superuser)
        self.assertDownloadLogoDefault(company=self.company2)
        self.assertDownloadLogoDefault(user=self.user_company2)

    def test_set_logo_company_of_superuser(self):
        self.company_of_superuser.logo = self.gizeh_data_b64
        self.assertDownloadLogoGizeh()
        self.assertDownloadLogoGizeh(company=self.company_of_superuser)
        self.assertDownloadLogoGizeh(user=self.user_of_company_of_superuser)
        self.assertDownloadLogoDefault(company=self.company2)
        self.assertDownloadLogoDefault(user=self.user_company2)

    def test_set_logo_other_company(self):
        self.company2.logo = self.gizeh_data_b64
        self.assertDownloadLogoDefault()
        self.assertDownloadLogoGizeh(company=self.company2)
        self.assertDownloadLogoGizeh(user=self.user_company2)
        self.assertDownloadLogoDefault(company=self.company_of_superuser)
        self.assertDownloadLogoDefault(user=self.user_of_company_of_superuser)

    def test_set_no_logo_company_of_superuser(self):
        self.company_of_superuser.logo = None
        self.assertDownloadLogoNoLogo()
        self.assertDownloadLogoNoLogo(company=self.company_of_superuser)
        self.assertDownloadLogoNoLogo(user=self.user_of_company_of_superuser)
        self.assertDownloadLogoDefault(company=self.company2)
        self.assertDownloadLogoDefault(user=self.user_company2)

    def test_set_no_logo_other_company(self):
        self.company2.logo = None
        self.assertDownloadLogoDefault()
        self.assertDownloadLogoNoLogo(company=self.company2)
        self.assertDownloadLogoNoLogo(user=self.user_company2)
        self.assertDownloadLogoDefault(company=self.company_of_superuser)
        self.assertDownloadLogoDefault(user=self.user_of_company_of_superuser)

    def test_company_param_win_on_current_user(self):
        """When company and user are specified, company wins (ex: in an email you see the company logo and not yours)"""
        self.company_of_superuser.logo = self.gizeh_data_b64
        self.assertDownloadLogoGizeh(company=self.company_of_superuser, user=self.user_company2)
        self.assertDownloadLogoDefault(company=self.company2, user=self.user_of_company_of_superuser)


@tagged('post_install', '-at_install')
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
        self.assertEqual(res1.headers.get('Cache-Control'), 'public, max-age=31536000, immutable')  # one year
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


@tagged('post_install', '-at_install')
class TestHttpStaticUpload(TestHttpStaticCommon):
    def _test_upload_small_file(self):
        new_test_user(self.env, 'jackoneill')
        self.authenticate('jackoneill', 'jackoneill')

        with RecordCapturer(self.env['ir.attachment'], []) as capture, \
             file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
            file_content = file.read()
            file_size = len(file_content)
            file.seek(0)
            res = self.opener.post(
                f'{self.base_url()}/web/binary/upload_attachment',
                files={'ufile': file},
                data={
                    'csrf_token': odoo.http.Request.csrf_token(self),
                    'model': 'test_http.stargate',
                    'id': self.env.ref('test_http.earth').id,
                },
            )
        res.raise_for_status()

        self.assertEqual(len(capture.records), 1, "An attachment should have been created")
        self.assertEqual(capture.records.name, 'gizeh.png')
        self.assertEqual(capture.records.raw, file_content)
        self.assertEqual(capture.records.mimetype, 'image/png')

        self.assertEqual(res.json(), [{
            'filename': 'gizeh.png',
            'mimetype': 'image/png',
            'id': capture.records.id,
            'size': file_size,
        }])

    def test_upload_small_file_without_icp(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'web.max_file_upload_size', False,
        )
        self._test_upload_small_file()

    def test_upload_small_file_with_icp(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'web.max_file_upload_size', 16386,  # gizen.png is smaller
        )
        self._test_upload_small_file()

    def test_upload_large_file(self):
        new_test_user(self.env, 'jackoneill')
        self.authenticate('jackoneill', 'jackoneill')

        with RecordCapturer(self.env['ir.attachment'], []) as capture, \
             file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
            file_size = file.seek(0, 2)
            file.seek(0)
            self.env['ir.config_parameter'].sudo().set_param(
                'web.max_file_upload_size', file_size - 1,
            )
            res = self.opener.post(
                f'{self.base_url()}/web/binary/upload_attachment',
                files={'ufile': file},
                data={
                    'csrf_token': odoo.http.Request.csrf_token(self),
                    'model': 'test_http.stargate',
                    'id': self.env.ref('test_http.earth').id,
                    'callback': 'callmemaybe',
                },
            )
        self.assertFalse(capture.records, "No attachment should have been created")
        self.assertEqual(res.status_code, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
