# -*- coding: utf-8 -*-
import openobject.templating

class FormEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/controllers/templates/form.mako']
    MAIN_FORM_BODY = u'id="main_form_body"'

    def insert_share_button(self, output):
        # Insert the share button on the form title H1 line, at the very end,
        # but only if the user is a member of the sharing group 
        share_opener_insertion = output.index(
                '</h1>',
                output.index(self.MAIN_FORM_BODY)) - 1
        return output[:share_opener_insertion] + '''
    <%
        if 'has_share' not in cp.session:
            cp.session['has_share'] = rpc.RPCProxy('share.wizard').has_share()
    %>
    % if cp.session['has_share'] and buttons.toolbar and not is_dashboard:
        <a id="share-opener" href="#share" title="${_('Share this in 2 clicks...')}">
            <img id="share-opener-img" src="/share/static/images/share.png"/>
        </a>
               <script type="text/javascript">
                   jQuery(document).ready(function() {
                       jQuery("#share-opener").click(function() {
                           jQuery(this).attr(
                               "href",
                               openobject.http.getURL('/share', {
                                   context: jQuery("#_terp_context").val(),
                                   domain: jQuery("#_terp_domain").val(),
                                   view_id: jQuery("#_terp_view_id").val(),
                                   action_id: jQuery("#_terp_action_id").val(),
                                   search_domain: jQuery("#_terp_view_type").val() == "form" ? 
                                                         ("[('id','=',"+jQuery("#_terp_id").val()+")]") : 
                                                            jQuery("#_terp_search_domain").val(),
                           }));
                       });
                   });
               </script>
               \n
    % endif
''' + output[share_opener_insertion:]

    def edit(self, template, template_text):
        return self.insert_share_button(
            super(FormEditor, self).edit(template, template_text))


class SidebarEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/widgets/templates/sidebar.mako']
    ADD_SHARE_SECTION = u'id="sidebar"'

    def insert_share_link(self, output):
        # Insert the link on the line, right after the link to open the
        # attachment form, but only if the user is a member of the sharing group 
        share_opener_insertion = output.index(
                '\n',
                output.index(self.ADD_SHARE_SECTION)) + 1
        return output[:share_opener_insertion] + '''
    <%
        if 'has_share' not in cp.session:
            cp.session['has_share'] = rpc.RPCProxy('share.wizard').has_share()
    %>
    % if cp.session['has_share']:
        <div id="share-wizard" class="sideheader-a"><h2>${_("Sharing")}</h2></div>
             <ul class="clean-a">
                 <li>
                     <a id="sharing" href="#share">${_("Share")}</a>
                 </li>
             </ul>
               <script type="text/javascript">
                   jQuery(document).ready(function() {
                       jQuery("#sharing").click(function() {
                           jQuery(this).attr(
                               "href",
                               openobject.http.getURL('/share', {
                                   context: jQuery("#_terp_context").val(),
                                   domain: jQuery("#_terp_domain").val(),
                                   view_id: jQuery("#_terp_view_id").val(),
                                   action_id: jQuery("#_terp_action_id").val(),
                                   search_domain: jQuery("#_terp_view_type").val() == "form" ? 
                                                         ("[('id','=',"+jQuery("#_terp_id").val()+")]") : 
                                                            jQuery("#_terp_search_domain").val(),
                           }));
                       });
                   });
               </script>
               \n
    % endif
''' + output[share_opener_insertion:]

    def edit(self, template, template_text):
        return self.insert_share_link(
            super(SidebarEditor, self).edit(template, template_text))
