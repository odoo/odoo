# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect

from odoo import http, _
from odoo.http import request
from odoo.osv import expression

from odoo.addons.website.controllers import form

class WebsiteHelpdesk(http.Controller):

    def get_helpdesk_team_data(self, team, search=None):
        return {
            'team': team,
            'main_object': team,
        }

    @http.route(['/helpdesk', '/helpdesk/<model("helpdesk.team"):team>'], type='http', auth="public", website=True, sitemap=True)
    def website_helpdesk_teams(self, team=None, **kwargs):
        search = kwargs.get('search')

        teams_domain = [('use_website_helpdesk_form', '=', True)]
        if not request.env.user.has_group('helpdesk.group_helpdesk_manager'):
            if team and not team.is_published:
                raise NotFound()
            teams_domain = expression.AND([teams_domain, [('website_published', '=', True)]])

        if team and team.show_knowledge_base and not kwargs.get('contact_form'):
            return redirect(team.website_url + '/knowledgebase')

        teams = request.env['helpdesk.team'].search(teams_domain, order="id asc")
        if not teams:
            raise NotFound()

        result = self.get_helpdesk_team_data(team or teams[0], search=search)
        result['multiple_teams'] = len(teams) > 1
        return request.render("website_helpdesk.team", result)

    def _get_knowledge_base_values(self, team):
        return {
            'team': team,
            'main_object': team,
        }

    @http.route(['/helpdesk/<model("helpdesk.team"):team>/knowledgebase'], type='http', auth="public", website=True, sitemap=True)
    def website_helpdesk_knowledge_base(self, team, **kwargs):
        if not team.show_knowledge_base:
            return redirect(team.website_url)

        search = kwargs.get('search')
        search_kw = ['type', 'date', 'tag']
        if search is not None:
            searches = {
                'search': search,
                **{k: kwargs.get(k) for k in search_kw if request.website.is_view_active('website_helpdesk.navbar_search_%s' % k)}
            }

            types = team._helpcenter_filter_types()
            options = team._get_search_options(searches)
            search_types = [searches['type']] if searches.get('type') else types.keys()
            results = self._get_search_results(search, search_types, options)

            tags = sorted(set(team._helpcenter_filter_tags(kwargs.get('type'))))
            dates = {
                '7days': _('Last Week'),
                '30days': _('Last Month'),
                '365days': _('Last Year'),
            }
            return request.render("website_helpdesk.search_results", {
                'team': team,
                'search': search,
                'search_count': len(results),
                'searches': searches,
                'available_types': types,
                'current_type': types[searches['type']] if searches.get('type') else False,
                'available_dates': dates,
                'current_date': dates[searches['date']] if searches.get('date') else False,
                'available_tags': tags,
                'current_tag': searches['tag'] if searches.get('tag') else False,
                'results': results,
            })

        return request.render("website_helpdesk.knowledge_base", self._get_knowledge_base_values(team))

    @http.route(['/helpdesk/<model("helpdesk.team"):team>/knowledgebase/autocomplete'], type='json', auth="public", website=True, sitemap=True)
    def website_helpdesk_autocomplete(self, team, **kwargs):
        if not team.show_knowledge_base:
            raise NotFound()

        search = kwargs.get('term')
        if len(search) < 3:
            return {'results': [], 'showMore': False}

        searches = {'search': search}
        options = team._get_search_options(searches)

        search_types = team._helpcenter_filter_types().keys()
        results = self._get_search_results(search, search_types, options)

        return {
            'results': [{
                'name': r['record'].name,
                'icon': r['icon'],
                'url': r['url']} for r in results[:10]],
            'showMore': len(results) > 10,
        }

    def _get_search_results(self, search, search_types, options):
        search_results = []
        if search:
            for search_type in search_types:
                count, results, dummy = request.website._search_with_fuzzy(search_type, search, limit=10, order='name', options=options)
                if count:
                    for all_results in results:
                        if all_results.get('results', False):
                            search_results += self._format_search_results(search_type, all_results['results'], options)
        return sorted(search_results, key=lambda res: res.get('score', 0), reverse=True)

    def _format_search_results(self, search_type, records, options):
        return []

class WebsiteForm(form.WebsiteForm):

    def _handle_website_form(self, model_name, **kwargs):
        email = request.params.get('partner_email')
        if email:
            if request.env.user.email == email:
                partner = request.env.user.partner_id
            else:
                partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'email': email,
                    'name': request.params.get('partner_name', False),
                    'lang': request.lang.code,
                })
            request.params['partner_id'] = partner.id

        return super(WebsiteForm, self)._handle_website_form(model_name, **kwargs)

    def insert_attachment(self, model, id_record, files):
        super().insert_attachment(model, id_record, files)
        # If the helpdesk ticket form is submit with attachments,
        # Give access token to these attachments and make the message
        # accessible to the portal user
        # (which will be able to view and download its own documents).
        model_name = model.model
        if model_name == "helpdesk.ticket":
            ticket = model.env[model_name].browse(id_record)
            attachments = request.env['ir.attachment'].sudo().search([('res_model', '=', model_name), ('res_id', '=', ticket.id), ('access_token', '=', False)])
            attachments.generate_access_token()
            message = ticket.message_ids.filtered(lambda m: m.attachment_ids == attachments)
            message.is_internal = False
            message.subtype_id = request.env.ref('mail.mt_comment')
