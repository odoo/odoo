# -*- coding: utf-8 -*-
from openerp import http, SUPERUSER_ID, fields
from openerp.http import request
from openerp.tools import html_escape
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_crm.controllers.main import contactus

class PageController(Website):

    @http.route('/page/<page:page>', auth="public", website=True)
    def page(self, page, **opt):
        response = super(PageController, self).page(page, **opt)
        # duplication of ir_http.py

        if getattr(response, 'status_code', 0) == 200:
            try:
                view = request.website.get_template(page)
            except:
                pass  # view not found
            else:
                if view.track:  # avoid tracking redirected page
                    cr, uid, context = request.cr, request.uid, request.context
                    lead_id = request.env["crm.lead"].decode(request)
                    url = request.httprequest.url
                    vals = {'lead_id': lead_id, 'user_id': request.session.get('uid'), 'url': url}

                    if not lead_id or request.registry['website.crm.pageview'].create_pageview(cr, uid, vals, context=context):
                        # create_pageview failed
                        response.delete_cookie('lead_id')
                        request.session.setdefault('pages_viewed', {})[url] = fields.Datetime.now()
                        request.session.modified = True

        return response


class ContactController(contactus):

    @http.route(['/crm/contactus'], type='http', auth="public", website=True)
    def contactus(self, **kwargs):
        response = super(ContactController, self).contactus(**kwargs)
        # the cookie is written here because the response is not available in the create_lead function
        if '_values' in response.qcontext:  # contactus error : fields validation not passed
            # NOTE: this requires for the lead_id to be added to values in the parent controller
            lead_id = response.qcontext.get('_values').get('lead_id')
            if lead_id:  # a new lead has been created
                lead_model = request.registry['crm.lead']
                # sign the lead_id
                sign = lead_model.encode(lead_id)
                response.set_cookie('lead_id', sign, domain=lead_model.get_score_domain_cookies())
        return response

    def create_real_lead(self, request, values, kwargs):
        """ Make this function overridable to create a lead with another function that create_lead from webiste_crm """
        return super(ContactController, self).create_lead(request, values, kwargs)

    def create_lead(self, request, values, kwargs):
        cr, context = request.cr, request.context

        lead_model = request.registry["crm.lead"]
        lead_id = lead_model.decode(request)

        # domain: leads that are still open:
        # NOT [ on_change AND (proba = 0 OR proba = 100) ]
        # the condition on the lead_id is prepended
        domain = [
            ('id', '=', lead_id),
            '|',
            ('stage_id.on_change', '=', False),
            '&',
            ('stage_id.probability', '!=', 0),
            ('stage_id.probability', '!=', 100)
        ]
        lead_instance = lead_model.search(cr, SUPERUSER_ID, domain, context=context)

        if lead_instance:
            # a lead_id cookie exists and it has not been altered and the lead is not closed
            lead = lead_model.browse(cr, SUPERUSER_ID, lead_id, context=context)

            # NOTE: the following should be changed when dynamic forms exist
            changed_values = {}
            for fieldname, fieldvalue in values.items():
                if fieldname in lead._all_columns and fieldvalue:
                    if lead[fieldname] and lead[fieldname] != fieldvalue:
                        changed_values[fieldname] = fieldvalue
                    else:
                        lead[fieldname] = fieldvalue
            # Post a message to indicate the updated field (if any)
            if changed_values:
                body = 'Other value given for field '
                for fieldname in changed_values.keys():
                    body += '<br/><b>%s</b>: <b>%s</b>' % (fieldname, html_escape(changed_values[fieldname]))
                request.registry['crm.lead'].message_post(cr, SUPERUSER_ID, [lead_id], body=body, subject="Field value changed", context=context)

        else:
            # either no lead_id cookie OR the lead_id doesn't exist in db OR the current one is closed -> a lead is created
            lang = context.get('lang', False)
            lang_id = request.registry["res.lang"].search(cr, SUPERUSER_ID, [('code', '=', lang)], context=context)
            lang_id = lang_id and lang_id[0] or False
            values['lang_id'] = lang_id
            body = None

            if 'pages_viewed' in request.session:
                score_pageview_ids = []
                url_list = []
                pages_viewed = request.session['pages_viewed']
                for url, date in pages_viewed.iteritems():
                    vals = {'user_id': request.session.get('uid'), 'url': url, 'view_date': date}
                    score_pageview_ids.append((0, 0, vals))
                    url_list.append(url)
                del request.session['pages_viewed']
                values['score_pageview_ids'] = score_pageview_ids
                urls = []
                for url in url_list:
                    url_encoded = html_escape(url)
                    urls.append('<a href="%s" target="_blank"><b>%s</b></a>' % (url_encoded, url_encoded))
                body = '<br/>'.join(urls)

            new_lead_id = self.create_real_lead(request, values, kwargs)

            # if pages were seen, a message is posted
            if body:
                request.registry['crm.lead'].message_post(cr, SUPERUSER_ID, [new_lead_id], body=body, subject="Pages visited", context=context)

            return new_lead_id
