# To change this template, choose Tools | Templates
# and open the template in the editor.
from osv import fields,osv
import pooler
import netsvc
import re

class email_template_engines(osv.osv):
    _name = "email_template.engines"
    _description = "Email Template Engine"

#    def __init__(self):
#        print "Started Engine"

    def check(self):
        print "Start self check"
        
    def strip_html(self,text):
        #Removes HTML, Have to check if still relevent
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
        #print cr,uid,id,message,templateid,context
        if message:
            logger = netsvc.Logger()
            def merge(match):
                template = self.pool.get("email.template").browse(cr,uid,templateid,context)
                obj_pool = self.pool.get(template.object_name.model)
                obj = obj_pool.browse(cr, uid, id, context)
                exp = str(match.group()[2:-2]).strip()
                #print "level 1:",exp
                exp_spl = exp.split('/')
                #print "level 2:",exp_spl
                try:
                    result = eval(exp_spl[0], {'object':obj,})
                except:
                    result = "Rendering Error"
                #print "result:",result
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
