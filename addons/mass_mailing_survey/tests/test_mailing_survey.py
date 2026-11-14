# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import parse_qsl, urlsplit

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('link_tracker', 'mailing_portal', 'post_install', '-at_install')
class TestMailingSurvey(MassMailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_mailing_list()
        cls.test_contact = cls.mailing_list_1.contact_ids[0]

        cls.test_survey = cls.env['survey.survey'].create({
            'access_mode': 'public',
            'title': 'Customer Satisfaction',
        })
        cls.test_mailing = cls.env['mailing.mailing'].create({
            'body_html': f"""<p>
                <a id="survey" href="{cls.test_survey.get_start_url()}">Take our survey</a>
                <a id="url" href="https://www.example.com/foo/bar">Other link</a>
            </p>""",
            'contact_list_ids': [(4, cls.mailing_list_1.id)],
            'mailing_model_id': cls.env['ir.model']._get_id('mailing.list'),
            'mailing_type': 'mail',
            'subject': 'TestMailing with Survey',
        })

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mass_mailing.models.mailing')
    def setUp(self):
        super().setUp()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            self.test_mailing.action_send_mail()
        mail = self._find_mail_mail_wrecord(self.test_contact)
        self.mailing_trace = mail.mailing_trace_ids
        self.survey_code = self._get_code_from_short_url(self._get_href_from_anchor_id(mail.body, 'survey'))
        self.url_code = self._get_code_from_short_url(self._get_href_from_anchor_id(mail.body, 'url'))

    def _click(self, code, trace_id=None):
        response = self.url_open(f'/r/{code.code}/m/{trace_id or self.mailing_trace.id}', allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        return dict(parse_qsl(urlsplit(response.headers['Location']).query))

    def _get_answers(self):
        return self.env['survey.user_input'].search([('survey_id', '=', self.test_survey.id)])

    def test_link_tracker_title(self):
        """Local survey links are titled after the survey, other links keep the default title."""
        self.assertEqual(self.survey_code.link_id.title, 'Customer Satisfaction')
        base_url = self.test_survey.get_base_url()
        token = self.test_survey.access_token
        for url, title in [
            (f'{base_url}/survey/start/{token}/', 'Customer Satisfaction'),  # trailing slash
            (f'https://other.example.com/survey/start/{token}', 'Test_TITLE'),  # other website
            (f'{base_url}/survey/start/unknown-token', 'Test_TITLE'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.env['link.tracker']._get_title_from_url(url), title)

    def test_click_creates_and_reuses_answer(self):
        """A public click creates an answer for the recipient's email, next clicks
        reuse it as long as it is not started."""
        query = self._click(self.survey_code)
        answer = self._get_answers()
        self.assertEqual(len(answer), 1)
        self.assertEqual(answer.email, self.mailing_trace.email)
        self.assertFalse(answer.partner_id)
        self.assertEqual(answer.state, 'new')
        self.assertEqual(query.get('answer_token'), answer.access_token)

        query = self._click(self.survey_code)
        self.assertEqual(self._get_answers(), answer, 'Should not create a new answer at each click')
        self.assertEqual(query.get('answer_token'), answer.access_token)

    def test_click_started_answer(self):
        """A started answer's token is never given: only the email is passed."""
        self._click(self.survey_code)
        answer = self._get_answers()
        answer.state = 'in_progress'

        query = self._click(self.survey_code)
        self.assertEqual(self._get_answers(), answer)
        self.assertNotIn('answer_token', query)
        self.assertEqual(query.get('email'), self.mailing_trace.email)

    def test_click_ignored(self):
        """The url is left unchanged and no answer is created when:
           - No trace_id is given
           - The trace_id does not exist
           - The trace_id belongs to another mailing"""
        other_trace = self._create_sent_traces(self.test_mailing.copy(), self.test_contact)
        for description, code, trace_id in [
            ('Not a survey link', self.url_code, None),
            ('Unknown trace', self.survey_code, self.mailing_trace.id + 1000),
            ('Trace of another mailing', self.survey_code, other_trace.id),
        ]:
            with self.subTest(description):
                query = self._click(code, trace_id)
                self.assertNotIn('answer_token', query)
                self.assertNotIn('email', query)
                self.assertFalse(self._get_answers())

    def test_click_archived_survey(self):
        """Archived surveys are left to the survey controller."""
        self.test_survey.active = False
        query = self._click(self.survey_code)
        self.assertNotIn('answer_token', query)
        self.assertFalse(self._get_answers())

    def test_click_logged_user(self):
        """Logged users are left to the survey controller, which creates the
        answer for them."""
        self.authenticate('user_marketing', 'user_marketing')
        query = self._click(self.survey_code)
        self.assertNotIn('answer_token', query)
        self.assertNotIn('email', query)
        self.assertFalse(self._get_answers())
