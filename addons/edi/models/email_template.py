# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011-2012 OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
from edi import EDIMixin

class LazyEdiWebUrlViewGetter(object):
    """
    This class allow to generate EDI web view url only when the template
    really use it (lazy mode)
    """
    def __init__(self, cr, uid, model_obj, res_id, context):
        self.cr = cr
        self.uid = uid
        self.model_obj = model_obj
        self.res_id = res_id
        self.context = context
        self.web_view_url = None

    def get_web_view_url(self):
        """
        generate and return web_view_url of the current object
        :return: unicode string
        """
        if self.web_view_url is None:
            record = self.model_obj.browse(self.cr, self.uid, self.res_id, context=self.context)
            self.web_view_url = self.model_obj._edi_get_object_web_url_view(self.cr, self.uid, record, context=self.context)
        return self.web_view_url

    def __unicode__(self):
        return self.get_web_view_url()
    __str__ = __unicode__

    def __nonzero__(self):
        # handle ctx.get('edi_web_view_url') or 'n/a' things
        return self.get_web_view_url() and True or False

class email_template(osv.osv):
    _inherit = 'email.template'

    def _prepare_render_template_context(self, cr, uid, model, res_id, context=None):
        render_context = super(email_template, self)._prepare_render_template_context(cr, uid, model, res_id, context=context)

        # add 'edi_web_url_view' lazy object for all EDI objects, but do not override it
        # if it's already present (forced by someone else)
        model_obj = self.pool.get(model)
        if isinstance(model_obj, EDIMixin) and not 'edi_web_url_view' in render_context:
            render_context = render_context.copy()
            render_context['edi_web_url_view'] = LazyEdiWebUrlViewGetter(cr, uid, model_obj, res_id, context)

        return render_context

