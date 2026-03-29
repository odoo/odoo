import base64

import odoo.tests

from odoo.addons.website.tools import MockRequest


class TestReports(odoo.tests.HttpCase):
    def test_report_session_cookie(self):
        """ Asserts wkhtmltopdf forwards the user session when requesting resources to Odoo, such as images,
        and that the resource is correctly returned as expected.
        """
        partner_id = self.env.user.partner_id.id
        img = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC'
        image = self.env['ir.attachment'].create({
            'name': 'foo',
            'res_model': 'res.partner',
            'res_id': partner_id,
            'datas': img,
        })
        report = self.env['ir.actions.report'].create({
            'name': 'test report',
            'report_name': 'base.test_report',
            'model': 'res.partner',
        })
        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'base.test_report',
            'key': 'base.test_report',
            'arch': f'''
                <main>
                    <div class="article" data-oe-model="res.partner" t-att-data-oe-id="docs.id">
                        <img src="/web/image/{image.id}"/>
                    </div>
                </main>
            '''
        })

        result = {}
        origin_content_image = self.env.registry['ir.http']._content_image

        def _content_image(self, *args, **kwargs):
            result['uid'] = self.env.uid
            response = origin_content_image(self, *args, **kwargs)
            result['data'] = response.data
            return response

        self.patch(self.env.registry['ir.http'], '_content_image', _content_image)

        # 1. Request the report as admin, who has access to the image
        admin = self.env.ref('base.user_admin')
        report = report.with_user(admin)
        with MockRequest(report.env) as mock_request:
            mock_request.session.sid = self.authenticate(admin.login, admin.login).sid
            report.with_context(force_report_rendering=True)._render_qweb_pdf([partner_id])

        self.assertEqual(
            result.get('uid'), admin.id, 'wkhtmltopdf is not fetching the image as the user printing the report'
        )
        self.assertEqual(base64.b64encode(result.get('data')), img, 'wkhtmltopdf did not fetch the right image content')

        # 2. Request the report as public, who has no acess to the image
        self.logout()
        result.clear()
        public = self.env.ref('base.public_user')
        report = report.with_user(public)
        with MockRequest(self.env) as mock_request:
            report.with_context(force_report_rendering=True)._render_qweb_pdf([partner_id])

        self.assertEqual(
            result.get('uid'), public.id, 'wkhtmltopdf is not fetching the image as the user printing the report'
        )
        self.assertNotEqual(
            base64.b64encode(result.get('data')), img,
            'wkhtmltopdf must not have been allowed to fetch the image and fetch a placeholder instead'
        )
