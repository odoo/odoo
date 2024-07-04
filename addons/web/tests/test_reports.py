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
        origin_find_record = self.env.registry['ir.binary']._find_record

        def _find_record(self, xmlid=None, res_model='ir.attachment', res_id=None, access_token=None, field=None):
            if res_model == 'ir.attachment' and res_id == image.id:
                result['uid'] = self.env.uid
                record = origin_find_record(self, xmlid, res_model, res_id, access_token, field)
                result.update({'record_id': record.id, 'data': record.datas})
            else:
                record = origin_find_record(self, xmlid, res_model, res_id, access_token, field)
            return record

        self.patch(self.env.registry['ir.binary'], '_find_record', _find_record)

        # 1. Request the report as admin, who has access to the image
        admin = self.env.ref('base.user_admin')
        report = report.with_user(admin)
        with MockRequest(report.env) as mock_request:
            mock_request.session.sid = self.authenticate(admin.login, admin.login).sid
            report.with_context(force_report_rendering=True)._render_qweb_pdf(report.id, [partner_id])

        self.assertEqual(
            result.get('uid'), admin.id, 'wkhtmltopdf is not fetching the image as the user printing the report'
        )
        self.assertEqual(result.get('record_id'), image.id, 'wkhtmltopdf did not fetch the expected record')
        self.assertEqual(result.get('data'), img, 'wkhtmltopdf did not fetch the right image content')

        # 2. Request the report as public, who has no acess to the image
        self.logout()
        result.clear()
        public = self.env.ref('base.public_user')
        report = report.with_user(public)
        with MockRequest(self.env) as mock_request:
            report.with_context(force_report_rendering=True)._render_qweb_pdf(report.id, [partner_id])

        self.assertEqual(
            result.get('uid'), public.id, 'wkhtmltopdf is not fetching the image as the user printing the report'
        )
        self.assertEqual(result.get('record_id'), None, 'wkhtmltopdf must not have been allowed to fetch the image')
        self.assertEqual(result.get('data'), None, 'wkhtmltopdf must not have been allowed to fetch the image')
