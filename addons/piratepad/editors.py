# -*- coding: utf-8 -*-

from openobject.widgets import JSLink
import openobject.templating

class SidebarTemplateEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/widgets/templates/sidebar.mako']
    BINARY_ATTACHMENTS_FORM = u'<form id="attachment-box"'

    def edit(self, template, template_text):
        output = super(SidebarTemplateEditor, self).edit(template, template_text)

        insertion_point = output.index(self.BINARY_ATTACHMENTS_FORM)
        return output[:insertion_point] + '''
            <form id="pad-box" action="/piratepad/link" method="post">
                <label for="sidebar_pad_datas">${_("Name")}:</label>
                <table width="100%">
                <tr>
                   <td width=60% style="padding-right:8px;">
                        <input type="text" id="sidebar_pad_datas" class="binary"
                       name="pad_name" kind="url" size="5" />
                   </td>
                    <td>
                        <a href="#" id="sidebar_pad_ok" class="button-a">${_("Ok")}</a>
                    </td>
                </tr>
               </table>
            </form>
            <script type="text/javascript">
                jQuery(document).ready(function() {

                    var padForm = jQuery('#pad-box').hide();

                    jQuery('#attachments').prev().append(
                        jQuery('<a>',{
                            'href': '#',
                            'id': 'add-pad',
                            'class': 'button-a',
                        }).text('${_("Pad")}')
                    );
                    jQuery('#sidebar_pad_ok').bind('click', function(){
                        padForm.submit();
                    });
                    jQuery('#add-pad').click(function(e){
                        padForm.show();
                        e.preventDefault();
                    });
                    padForm.bind({
                        submit: createAttachment
                    });
                });
            </script>
        ''' + output[insertion_point:]
