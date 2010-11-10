# -*- coding: utf-8 -*-
import openobject.templating

class SidebarTemplateEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/widgets/templates/sidebar.mako']
    ADD_SHARE_BUTTON = u'id="sidebar"'

    def insert_share_link(self, output):
        # Insert the link on the line right after the link to open the
        # attachment form
        form_opener_insertion = output.index(
                '\n',
                output.index(self.ADD_SHARE_BUTTON)) + 1
        output = output[:form_opener_insertion] + \
                 '''<div id="share-wizard" class="sideheader-a"><h2>${_("Share View")}</h2></div>
                     <ul class="clean-a">
                         <li>
                             <a id="share_view" href="javascript: void(0)"
                             style="right: 36px;"
                             >${_("Share")}</a>
                         </li>
                     </ul>
                       <script type="text/javascript">
                           jQuery(document).ready(function() {
                               jQuery('#share_view').click(function(){
                                   var _view_type = jQuery('#_terp_view_type').val();
                                   var _domain =  jQuery('#_terp_domain').val();
                                   var _search_domain =  jQuery('#_terp_search_domain').val();
                                   var _filter_domain =  jQuery('#_terp_filter_domain').val();
                                   var _context = jQuery('#_terp_context').val();
                                   var url = openobject.http.getURL('/share', {view_type: _view_type, domain: _domain, search_domain: _search_domain, filter_domain : _filter_domain, context: _context});
                                   window.open(url);
                               });
                           });
                       </script>
                       \n''' + \
                 output[form_opener_insertion:]
        return output

    def edit(self, template, template_text):
        output = super(SidebarTemplateEditor, self).edit(template, template_text)

        output = self.insert_share_link(output)
        return output