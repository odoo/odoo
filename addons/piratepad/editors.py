# -*- coding: utf-8 -*-
import openobject.templating

class SidebarTemplateEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/widgets/templates/sidebar.mako']
    ADD_ATTACHMENT_BUTTON = u'id="add-attachment"'
    BINARY_ATTACHMENTS_FORM = u'<form id="attachment-box"'

    def insert_pad_link(self, output):
        # Insert the link on the line right after the link to open the
        # attachment form
        form_opener_insertion = output.index(
                '\n',
                output.index(self.ADD_ATTACHMENT_BUTTON)) + 1
        output = output[:form_opener_insertion] + \
                 '<a href="#" id="add-pad" class="button-a">${_("Pad")}</a>\n' + \
                 output[form_opener_insertion:]
        return output

    def edit(self, template, template_text):
        output = super(SidebarTemplateEditor, self).edit(template, template_text)

        output = self.insert_pad_link(output)

        form_insertion_point = output.index(self.BINARY_ATTACHMENTS_FORM)
        return output[:form_insertion_point] + '''
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
        ''' + output[form_insertion_point:]
