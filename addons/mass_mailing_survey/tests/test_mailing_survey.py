# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import parse_qsl, urlencode, urlsplit

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('mass_mailing_survey', 'post_install', '-at_install')
class TestMailingSurvey(MassMailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_mailing_list()
        cls.test_contact = cls.mailing_list_1.contact_ids[0]

        cls.test_survey = cls.env['survey.survey'].create({
            'access_mode': 'public',
            'question_and_page_ids': [(0, 0, {'title': 'Comments', 'question_type': 'text_box'})],
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
        self.assertEqual(response.status_code, 301)
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

    def test_click_public(self):
        """A public click passes the recipient's email and the mailing to the survey
        controller, which creates the answer with them. No answer token is given."""
        query = self._click(self.survey_code)
        self.assertEqual(query.get('email'), self.mailing_trace.email)
        self.assertEqual(query.get('mass_mailing_id'), str(self.test_mailing.id))
        self.assertNotIn('answer_token', query)
        self.assertFalse(self._get_answers(), 'The answer is created by the survey controller')

        self.url_open(f'{self.test_survey.get_start_url()}?{urlencode(query)}', allow_redirects=False)
        answer = self._get_answers()
        self.assertEqual(len(answer), 1)
        self.assertEqual(answer.email, self.mailing_trace.email)
        self.assertEqual(answer.mass_mailing_id, self.test_mailing)
        self.assertFalse(answer.partner_id)

    def test_click_ignored(self):
        """The url is left unchanged when:
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
                self.assertNotIn('email', query)
                self.assertNotIn('mass_mailing_id', query)

    def test_click_archived_survey(self):
        """Archived surveys are left to the survey controller."""
        self.test_survey.active = False
        query = self._click(self.survey_code)
        self.assertNotIn('email', query)

    def test_click_logged_user(self):
        """Logged users only get the mailing: the survey controller creates the
        answer for their own partner."""
        self.authenticate('user_marketing', 'user_marketing')
        query = self._click(self.survey_code)
        self.assertEqual(query.get('mass_mailing_id'), str(self.test_mailing.id))
        self.assertNotIn('email', query)

    def test_start_invalid_mailing(self):
        """An invalid mass_mailing_id is ignored when creating the answer."""
        for mass_mailing_id in ('abc', str(self.test_mailing.id + 1000)):
            with self.subTest(mass_mailing_id=mass_mailing_id):
                response = self.url_open(
                    f'{self.test_survey.get_start_url()}?{urlencode({"mass_mailing_id": mass_mailing_id})}',
                    allow_redirects=False,
                )
                self.assertLess(response.status_code, 400)
        answers = self._get_answers()
        self.assertTrue(answers)
        self.assertFalse(answers.mass_mailing_id)
