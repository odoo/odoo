# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
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
import openobject.templating

class BaseTemplateEditor(openobject.templating.TemplateEditor):
    templates = ['/openobject/controllers/templates/base.mako']

    def edit(self, template, template_text):
        output = super(BaseTemplateEditor, self).edit(template, template_text)

        end_head = output.index('</head>')

        output = output[:end_head] + """
<link rel="stylesheet" type="text/css" href="/web_uservoice/static/css/uservoice.css"/>
        """ + output[end_head:]


        end_body = output.index('</body>')

        # testing forum: 84397
        output = output[:end_body] + """
<script type="text/javascript">
  var uservoiceOptions = {
    key: 'openerpsa',
    host: 'feedback.openerp.com',
    forum: '${getattr(cp.request, 'uservoice_forum', 77459)}',
    lang: 'en',
    showTab: false
  };
  function _loadUserVoice() {
    var s = document.createElement('script');
    s.src = ("https:" == document.location.protocol ? "https://" : "http://") + "cdn.uservoice.com/javascripts/widgets/tab.js";
    document.getElementsByTagName('head')[0].appendChild(s);
  }
  _loadSuper = window.onload;
  window.onload = (typeof window.onload != 'function') ? _loadUserVoice : function() { _loadSuper(); _loadUserVoice(); };
</script>
        """ + output[end_body:]

        return output


class HeaderTemplateEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/controllers/templates/header.mako']

    def edit(self, template, template_text):
        output = super(HeaderTemplateEditor, self).edit(template, template_text)

        PAT = '<ul class="tools">'

        ul = output.index(PAT)
        output = output[:ul] + """
            <p class="logout feedback"><a href="#" onclick="UserVoice.Popin.show(uservoiceOptions); return false;"><img src="/web_uservoice/static/images/uv_favicon.png" />feedback</a></p>
        """ + output[ul:]

        return output

