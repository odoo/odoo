# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
import tools
from tools.translate import _
import pooler
import logging

try:
    from mako.template import Template as MakoTemplate
except ImportError:
    logging.getLogger('init').warning("module email_template: Mako templates not installed")

def get_value(cr, uid, message=None, model=None, record_id=False, context=None):
    """
    returns Messages in Mako Template
    """
    pool = pooler.get_pool(cr.dbname)
    if message is None:
        message = {}
    #Returns the computed expression
    if message:
        try:
            message = tools.ustr(message)
            record = pool.get(model).browse(cr, uid, record_id, context=context)
            env = {
                'user': pool.get('res.users').browse(cr, uid, uid, context=context),
                'db': cr.dbname
               }
            templ = MakoTemplate(message, input_encoding='utf-8')
            reply = MakoTemplate(message).render_unicode(object=record, peobject=record, env=env, format_exceptions=True)
            if reply == 'False':
                reply = ''
            return reply
        except Exception:
            logging.exception("can't render %r", message)
            return u""
    else:
        return message


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

