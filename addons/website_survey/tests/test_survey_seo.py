# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSurveySeo(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.surveys = cls.env['survey.survey'].create([{
            'title': title,
            'access_mode': 'public',
            'users_login_required': False,
            'question_and_page_ids': [(0, 0, {
                'title': 'Question',
                'question_type': 'char_box',
            })],
        } for title in ('First Survey', 'Second Survey')])

    def _get_meta(self, url):
        """ Return the og:title, the page title and the main object of the page at url. """
        res = self.url_open(url)
        res.raise_for_status()  # Check Page Status before processing testes to avoid miss-false
        tree = html.fromstring(res.content)
        return (
            tree.xpath('string(//meta[@property="og:title"]/@content)'),
            tree.xpath('string(//head/title)').strip(),
            tree.xpath('string(//html/@data-main-object)'),
        )

    def test_survey_layout_templates_reviewed(self):
        """This test is done to check that every template using layout is handled
        with website activated. So if a new template is created in survey, it can fails
        if not handled for website
        If SEO is needed - add it to survey_templates
        If SEO is not needed - Add it in exluded template list of this test.
        """
        seo_templates = {
            'survey.survey_closed_expired',
            'survey.survey_page_fill',
            'survey.survey_page_print',
            'survey.survey_void_content',
        }
        excluded_templates = {
            'survey.survey_403_page',  # may not access the survey
            'survey.survey_access_error',  # may not access the survey
            'survey.survey_auth_required',  # auth is required to access the survey
            'survey.survey_page_statistics',  # results, for internal users only (No need to get SEO)
            'survey.survey_session_code',  # no survey yet
        }
        views = self.env['ir.ui.view'].search([
            ('key', '=like', 'survey.%'),
            ('type', '=', 'qweb'),
            ('inherit_id', '=', False),
            ('website_id', '=', False),
        ]).filtered(lambda view: 't-call="survey.layout"' in view.arch_db)
        self.assertEqual(
            set(views.mapped('key')), seo_templates | excluded_templates,
            "A survey template calling 'survey.layout' was added or removed: add it either to "
            "website_survey/views/survey_templates.xml if it displays the survey publicly, or "
            "to the excluded templates of this test otherwise.",
        )
        for key in seo_templates:
            view = self.env['ir.ui.view']._get_template_view(key)
            self.assertEqual(
                view._get_combined_arch().find('.//t[@t-call="survey.layout"]').get('t-args'),
                'survey._get_website_layout_values()',
                f"Survey template {key} should use the survey as main object",
            )

    def test_survey_page_custom_seo_is_per_survey(self):
        """ Custom SEO set on a survey does not leak to other surveys. """
        first, second = self.surveys
        first.write({
            'website_meta_title': 'Custom SEO Title',
            'website_meta_description': 'Custom SEO Description',
        })
        og_title = self._get_meta(f'/survey/start/{first.access_token}')[0]
        self.assertEqual(og_title, 'Custom SEO Title')
        og_title = self._get_meta(f'/survey/start/{second.access_token}')[0]
        self.assertEqual(og_title, 'Second Survey')

    def test_survey_page_default_seo(self):
        """ Each public survey page displaying the survey uses its own title, without any
        configuration, while error pages shown to users who may not access the survey must
        not disclose it. """
        first, second = self.surveys
        for survey in self.surveys:
            expected = (survey.title, f'{survey.title} | My Website', repr(survey))
            # start page
            self.assertEqual(self._get_meta(f'/survey/start/{survey.access_token}'), expected)
            # question page
            answer = survey._create_answer()
            answer._mark_in_progress()
            self.assertEqual(self._get_meta(f'/survey/{survey.access_token}/{answer.access_token}'), expected)
            # end page
            answer._mark_done()
            self.assertEqual(self._get_meta(f'/survey/{survey.access_token}/{answer.access_token}'), expected)
            # print page
            self.assertEqual(
                self._get_meta(f'/survey/print/{survey.access_token}?answer_token={answer.access_token}'),
                expected,
            )
        # error pages
        second.users_login_required = True
        for survey, url in (
            (first, f'/survey/{first.access_token}/wrong-token'),  # access error
            (second, f'/survey/start/{second.access_token}'),  # login required
        ):
            with self.subTest(url=url):
                og_title, title, main_object = self._get_meta(url)
                self.assertNotIn(survey.title, og_title)
                self.assertNotIn(survey.title, title)
                self.assertNotIn('survey.survey', main_object)
        # closed survey page:
        answer = first._create_answer()
        first.action_archive()
        self.assertEqual(
            self._get_meta(f'/survey/{first.access_token}/{answer.access_token}'),
            ('First Survey', 'First Survey | My Website', repr(first)),
        )

    def test_survey_page_description_seo(self):
        """ The survey description is used as default SEO description, unless a custom one is set. """
        first, second = self.surveys
        first.write({
            'description': '<p>First Description</p>',
            'website_meta_description': 'Custom SEO Description',
        })
        second.description = '<p>Second Description</p>'
        for survey, expected in (
            (first, 'Custom SEO Description'),
            (second, 'Second Description'),
        ):
            res = self.url_open(f'/survey/start/{survey.access_token}')
            res.raise_for_status()
            tree = html.fromstring(res.content)
            self.assertEqual(tree.xpath('string(//meta[@property="og:description"]/@content)'), expected)
            self.assertEqual(tree.xpath('string(//meta[@name="description"]/@content)'), expected)

    def test_survey_page_no_tracking(self):
        """ Survey pages are not tracked, as their URL gives access to the answers. """
        survey = self.surveys[0]
        res = self.url_open(f'/survey/start/{survey.access_token}')
        tree = html.fromstring(res.content)
        self.assertEqual(tree.xpath('//html/@data-main-object'), [repr(survey)])
        self.assertFalse(tree.xpath('//html/@data-tracking-enabled'))
