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
                 '''<a href="#" id="add-pad" class="button-a
                 attachment-button">${_("Write")}</a>\n''' + \
                 output[form_opener_insertion:]
        return output

    def edit(self, template, template_text):
        output = super(SidebarTemplateEditor, self).edit(template, template_text)

        output = self.insert_pad_link(output)

        form_insertion_point = output.index(self.BINARY_ATTACHMENTS_FORM)
        return output[:form_insertion_point] + '''
            <form id="pad-form" action="/piratepad/link" method="post">
                <label for="sidebar_pad_datas">${_("Name")}:</label>
                <input id="sidebar_pad_datas"
                       name="pad_name" size="5" />
                <button>${_("Ok")}</button>
            </form>
            <script type="text/javascript">
                jQuery(document).ready(function() {
                    var $padForm = jQuery('#pad-form')
                            .hide()
                            .submit(createAttachment);
                    jQuery('#add-pad').click(function(e){
                        $padForm.show();
                        jQuery('#sidebar_pad_datas').focus();
                        e.preventDefault();
                    });
                });
            </script>
        ''' + output[form_insertion_point:]
