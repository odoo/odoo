(function () {
    'use strict';

var widgets = openerp.web.form.widgets;
while(!widgets.map.html) {
    widgets = widgets.parent;
}
widgets.map.html = "openerp.web.form.FieldTextHtml";

openerp.web.form.FieldTextHtml = openerp.web.form.AbstractField.extend(openerp.web.form.ReinitializeFieldMixin, {
    template: 'FieldTextHtml',
    initialize_content: function() {
        var self = this;
        this.callback = _.uniqueId('FieldTextHtml_');
        window[this.callback] = function (EditorBar) {
            self.on_editor_loaded(EditorBar);
            delete window[self.callback];
        };

        var src = "/FieldTextHtml?"+
            (this.get("effective_readonly") ? "" : "enable_editor=1")+
            (openerp.session.debug ? "&debug" : "")+
            "&model="+this.view.model+
            "&field="+this.name+
            "&id="+(this.view.datarecord.id||'')+
            "&callback="+this.callback;

        this.$iframe = this.$el.find('iframe');
        this.$iframe.attr("src", src);
    },
    on_editor_loaded: function (EditorBar) {
        var self = this;
        this.editor = EditorBar;
        this.document = this.$iframe.contents()[0];
        $("#website-top-edit", this.document).hide();
        this.$content = $("#wrapwrap .o_editable:first", this.document);
        this.$content.one('content_changed', function () {
            self.trigger('changed_value');
        });
    },
    render_value: function() {
        if (!this.$content) {
            return;
        }
        this.$content.html(this.get('value') || '');
    },
    is_false: function() {
        return this.get('value') === false || this.get('value') === "";
    },
    get_value: function() {
        if (window[this.callback+"_save"]) {
            this.editor.snippets.clean_for_save();
            this.internal_set_value( this.$content.prop('innerHTML') );
        }
        return this.get('value');
    },
});

})();