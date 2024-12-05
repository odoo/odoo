import werkzeug

from odoo import http
from odoo.http import request


# DANE: These are compatibility controllers which will be removed in v19/20
class Survey(http.Controller):
    # ------------------------------------------------------------
    # TEST / RETRY SURVEY ROUTES
    # ------------------------------------------------------------

    def _get_new_url_params(self, survey_token, answer_token=False):
        survey_sudo = request.env['survey.survey'].with_context(active_test=False).sudo().search([('access_token', '=', survey_token)])
        answer_sudo = request.env['survey.user_input'].sudo()
        if not survey_sudo:
            raise request.not_found()

        if answer_token:
            answer_sudo = request.env['survey.user_input'].sudo().search([
                ('survey_id', '=', survey_sudo.id),
                ('access_token', '=', answer_token)
            ], limit=1)
            if not answer_sudo:
                raise request.not_found()
        if answer_sudo:
            return survey_sudo.id, answer_sudo.id
        else:
            return survey_sudo.id, None

    @http.route(['/survey/test/<string:survey_token>'], type='http', auth='user', website=True)
    def survey_test_old(self, survey_token, **kwargs):
        survey_id, _ = self._get_new_url_params(survey_token)
        new_url = f'/survey/test/{survey_id}/{survey_token}'
        query_string = werkzeug.urls.url_encode(kwargs)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route(['/survey/retry/<string:survey_token>/<string:answer_token>'], type='http', auth='public', website=True)
    def survey_retry_old(self, survey_token, answer_token, **post):
        survey_id, answer_id = self._get_new_url_params(survey_token, answer_token)
        new_url = f'/survey/retry/{survey_id}/{answer_id}/{survey_token}/{answer_token}'
        query_string = werkzeug.urls.url_encode(post)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route(['/survey/start/<string:survey_token>'], type='http', auth='public', website=True)
    def survey_start_old(self, survey_token, answer_token=None, answer_id=False, email=False, **post):
        if not answer_token:
            answer_token = request.cookies.get('survey_%s' % survey_token)

        survey_id, answer_id = self._get_new_url_params(survey_token, answer_token)
        new_url = f'/survey/start/{survey_id}/{survey_token}'
        query_string = werkzeug.urls.url_encode(
                dict(**post, answer_id=answer_id, email=email, answer_token=answer_token)
            )
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route(['/survey/<string:survey_token>/<string:answer_token>'], type='http', auth='public', website=True)
    def survey_display_page_old(self, survey_token, answer_token, survey_id=False, answer_id=False, **post):
        new_url = self._get_new_url(survey_token, answer_token, **post)
        return request.redirect(new_url)

    # --------------------------------------------------------------------------
    # ROUTES to handle question images + survey background transitions + Tool
    # --------------------------------------------------------------------------

    @http.route(['/survey/<string:survey_token>/get_background_image'], type='http', auth="public", website=True, sitemap=False)
    def survey_get_background_old(self, survey_token):
        survey_id, _ = self._get_new_url_params(survey_token)
        new_url = f'/survey/{survey_id}/{survey_token}/get_background_image'
        return request.redirect(new_url)

    @http.route(['/survey/<string:survey_token>/<int:section_id>/get_background_image'], type='http', auth="public", website=True, sitemap=False)
    def survey_section_get_background_old(self, survey_token, section_id):
        survey_id, _ = self._get_new_url_params(survey_token)
        new_url = f'/survey/{survey_id}/{survey_token}/{section_id}/get_background_image'
        return request.redirect(new_url)

    @http.route(['/survey/get_question_image/<string:survey_token>/<string:answer_token>/<int:question_id>/<int:suggested_answer_id>'], type='http', auth="public", website=True, sitemap=False)
    def survey_get_question_image_old(self, survey_token, answer_token, question_id, suggested_answer_id):
        survey_id, answer_id = self._get_new_url_params(survey_token)
        new_url = f'/survey/get_question_image/{survey_id}/{answer_id}/{survey_token}/{answer_token}/{question_id}/{suggested_answer_id}'
        return request.redirect(new_url)

    # ----------------------------------------------------------------
    # JSON ROUTES to begin / continue survey (ajax navigation) + Tools
    # ----------------------------------------------------------------

    @http.route(['/survey/begin/<string:survey_token>/<string:answer_token>'], type='jsonrpc', auth='public', website=True)
    def survey_begin_old(self, survey_token, answer_token, **post):
        survey_id, answer_id = self._get_new_url_params(survey_token)
        new_url = f'/survey/begin/{survey_id}/{answer_id}/{survey_token}/{answer_token}'
        query_string = werkzeug.urls.url_encode(post)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route(['/survey/next_question/<string:survey_token>/<string:answer_token>'], type='jsonrpc', auth='public', website=True)
    def survey_next_question_old(self, survey_token, answer_token, **post):
        survey_id, answer_id = self._get_new_url_params(survey_token)
        new_url = f'/survey/next_question/{survey_id}/{answer_id}/{survey_token}/{answer_token}'
        query_string = werkzeug.urls.url_encode(post)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route(['/survey/submit/<string:survey_token>/<string:answer_token>'], type='jsonrpc', auth='public', website=True)
    def survey_submit_old(self, survey_token, answer_token, **post):
        survey_id, answer_id = self._get_new_url_params(survey_token)
        new_url = f'/survey/submit/{survey_id}/{answer_id}/{survey_token}/{answer_token}'
        query_string = werkzeug.urls.url_encode(post)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    # ----------------------------------------------------------------
    # session manage controllers
    # ----------------------------------------------------------------

    @http.route('/survey/session/manage/<string:survey_token>', type='http', auth='user', website=True)
    def survey_session_manage_old(self, survey_token, **kwargs):
        survey_id, _ = self._get_new_url_params(survey_token)
        new_url = f'survey/session/manage/{survey_id}/{survey_token}'
        query_string = werkzeug.urls.url_encode(kwargs)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route('/survey/session/next_question/<string:survey_token>', type='jsonrpc', auth='user', website=True)
    def survey_session_next_question_old(self, survey_token, go_back=False, **kwargs):
        survey_id, _ = self._get_new_url_params(survey_token)
        new_url = f'/survey/session/next_question/{survey_id}/{survey_token}'
        query_string = werkzeug.urls.url_encode(dict(**kwargs, go_back=go_back))
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route('/survey/session/results/<string:survey_token>', type='jsonrpc', auth='user', website=True)
    def survey_session_results_old(self, survey_token, **kwargs):
        survey_id, _ = self._get_new_url_params(survey_token)
        new_url = f'/survey/session/results/{survey_id}/{survey_token}'
        query_string = werkzeug.urls.url_encode(kwargs)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    @http.route('/survey/session/leaderboard/<string:survey_token>', type='jsonrpc', auth='user', website=True)
    def survey_session_leaderboard_old(self, survey_token, **kwargs):
        survey_id, _ = self._get_new_url_params(survey_token)
        new_url = f'/survey/session/leaderboard/{survey_id}/{survey_token}'
        query_string = werkzeug.urls.url_encode(kwargs)
        return request.redirect(f"{new_url}?{query_string}" if query_string else new_url)

    # ------------------------------------------------------------
    # QUICK ACCESS SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route('/s/<string:session_code>', type='http', auth='public', website=True)
    def survey_start_short_old(self, session_code):
        survey = request.env['survey.survey'].sudo().search([('session_code', '=', session_code)], limit=1)
        new_url = f'/s/{survey.id}/{session_code}'
        return request.redirect(new_url)

    @http.route('/survey/check_session_code/<string:session_code>', type='jsonrpc', auth='public', website=True)
    def survey_check_session_code_old(self, session_code):
        survey = request.env['survey.survey'].sudo().search([('session_code', '=', session_code)], limit=1)
        new_url = f'/survey/check_session_code/{survey.id}/{session_code}'
        return request.redirect(new_url)
