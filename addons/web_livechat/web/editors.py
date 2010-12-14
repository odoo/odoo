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
    <link rel="stylesheet" type="text/css" href="/web_livechat/static/css/lc.css"/>
    <%
        if 'livechat' not in cp.session:
            cp.session['livechat'] = rpc.session.execute('object', 'execute', 'publisher_warranty.contract', 'is_livechat_enable')
    %>
    % if cp.session['livechat']:
<script type="text/javascript">

  (function() {
    var lc_params = '';
    var lc_lang = 'en';
    var lc_skill = '0';

    var lc = document.createElement('script'); lc.type = 'text/javascript'; lc.async = true;
    var lc_src = ('https:' == document.location.protocol ? 'https://' : 'http://');
        lc_src += 'chat.livechatinc.net/licence/1035052/script.cgi?lang='+lc_lang+unescape('%26')+'groups='+lc_skill;
        lc_src += ((lc_params == '') ? '' : unescape('%26')+'params='+encodeURIComponent(encodeURIComponent(lc_params))); lc.src = lc_src;
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(lc, s);
  })();

</script>
    % endif
        """ + output[end_head:]

        return output


class HeaderTemplateEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/controllers/templates/header.mako']


    def edit(self, template, template_text):
        output = super(HeaderTemplateEditor, self).edit(template, template_text)

        PATTERN = '<div id="corner">'
        corner = output.index(PATTERN) + len(PATTERN)


        output = output[:corner] + """
            <p id="livechat_status" class="logout">
                ${ rpc.session.execute('object', 'execute', 'publisher_warranty.contract', 'get_default_livechat_text') | n}
            </p>
            % if cp.session['livechat']:

                <script type="text/javascript">
                  var __lc_buttons = __lc_buttons || [];
                  __lc_buttons.push({
                    elementId: 'livechat_status',
                    language: 'en',
                    skill: '0',
                    type: 'text',
                    labels: {
                      online: '<img src="/web_livechat/static/images/online.png"/>Need Help?',
                      offline: '<img src="/web_livechat/static/images/offline.png"/>Leave us a message'
                    }
                  });
                </script>

            % endif
        """ + output[corner:]
        return output

