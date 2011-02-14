# -*- coding: utf-8 -*-
import openobject.templating

class ShareActionEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/widgets/templates/sidebar.mako']
    ADD_SHARE_SECTION = u'id="sidebar"'

    def insert_share_link(self, output):
        # Insert the link on the line right after the link to open the
        # attachment form
        share_opener_insertion = output.index(
                '\n',
                output.index(self.ADD_SHARE_SECTION)) + 1
        return output[:share_opener_insertion] + \
               '''<div id="share-wizard" class="sideheader-a"><h2>${_("Sharing")}</h2></div>
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
                                           search_domain: jQuery("#_terp_search_domain").val(),
                                   }));
                               });
                           });
                       </script>
                       \n''' + \
                output[share_opener_insertion:]

    def edit(self, template, template_text):
        return self.insert_share_link(
            super(ShareActionEditor, self).edit(template, template_text))
