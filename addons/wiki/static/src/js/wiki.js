openerp.wiki = function (openerp) {
    openerp.web.form.widgets.add( 'text_wiki', 'openerp.web.form.FieldText');
/*
    openerp.wiki = {};
    openerp.wiki.FieldWikiReadonly = openerp.web.page.FieldCharReadonly.extend({
        set_value: function (value) {
            var show_value = wiky.process(value || '');
            this.$element.find('div').html(show_value);
            return show_value;
        }
    });
*/
};
