# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
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

from osv import osv
import re

class email_template_engines(osv.osv):
    _name = "email_template.engines"
    _description = "Email Template Engine"

    def check(self):
        pass
        
    def strip_html(self,text):
        #Removes HTML, Have to check if still relevant
        if text:
            def fixup(m):
                text = m.group(0)
                if text[:1] == "<":
                    return "" # ignore tags
                if text[:2] == "&#":
                    try:
                        if text[:3] == "&#x":
                            return unichr(int(text[3:-1], 16))
                        else:
                            return unichr(int(text[2:-1]))
                    except ValueError:
                        pass
                elif text[:1] == "&":
                    import htmlentitydefs
                    entity = htmlentitydefs.entitydefs.get(text[1:-1])
                    if entity:
                        if entity[:2] == "&#":
                            try:
                                return unichr(int(entity[2:-1]))
                            except ValueError:
                                pass
                        else:
                            return unicode(entity, "iso-8859-1")
                return text # leave as is
            return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)

    def parsevalue(self,cr,uid,id,message,templateid,context):
        #id: ID of the template's model's record to be used
        #message: the complete text including placeholders
        #templateid: the template id of the template
        #context: TODO
        if message:
            def merge(match):
                template = self.pool.get("email.template").browse(cr,uid,templateid,context)
                obj_pool = self.pool.get(template.object_name.model)
                obj = obj_pool.browse(cr, uid, id, context)
                exp = str(match.group()[2:-2]).strip()
                exp_spl = exp.split('/')
                try:
                    result = eval(exp_spl[0], {'object':obj,})
                except:
                    result = "Rendering Error"
                try:
                    if result in (None, False):
                        if len(exp_spl)>1:
                            return exp_spl[1]
                        else:
                            return 'Not Available'
                    return str(result)
                except:
                    return "Rendering Error"
            if message:
                com = re.compile('(\[\[.+?\]\])')
                retmessage = com.sub(merge, message)
            else:
                retmessage=""
            return retmessage

email_template_engines()
