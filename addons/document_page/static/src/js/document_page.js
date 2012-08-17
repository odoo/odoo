openerp.document_page = function (openerp) {
    openerp.web.form.widgets.add('text_wiki', 'openerp.web.form.FieldTextWiki');

    openerp.web.form.FieldTextWiki = openerp.web.form.FieldText.extend({
        render_value: function() {
            var show_value = openerp.web.format_value(this.get('value'), this, '');
            if (!this.get("effective_readonly")) {
                this.$textarea.val(show_value);
                if (show_value && this.view.options.resize_textareas) {
                    this.do_resize(this.view.options.resize_textareas);
                }
            } else {
                var wiki_value = wiky.process(show_value || '');
                this.$element.html(wiki_value);
            }
        },
    });
};
