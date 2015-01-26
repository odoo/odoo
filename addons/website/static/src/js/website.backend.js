(function () {
    'use strict';

var widgets = openerp.web.form.widgets;
while(!widgets.map.html) {
    widgets = widgets.parent;
}
widgets.map.html = "openerp.web.form.FieldTextHtml";

openerp.web.form.FieldTextHtml = openerp.web.form.AbstractField.extend(openerp.web.form.ReinitializeFieldMixin, {
    template: 'FieldTextHtml',
    get_url: function () {
        var src = this.options.editor_url ? this.options.editor_url+"?" : "/website/field/html?";

        var attr = {
            'model': this.view.model,
            'field': this.name,
            'res_id': this.view.datarecord.id || '',
            'callback': this.callback
        };
        if (this.options.snippets) {
            attr['snippets'] = this.options.snippets;
        }
        if (!this.get("effective_readonly")) {
            attr['enable_editor'] = 1;
        }
        if (openerp.session.debug) {
            attr['debug'] = 1;
        }

        for (var k in attr) {
            src += "&"+k+"="+attr[k];
        }
        return src;
    },
    initialize_content: function() {
        var self = this;
        this.callback = _.uniqueId('FieldTextHtml_');
        window.openerp[this.callback] = function (EditorBar) {
            self.on_editor_loaded(EditorBar);
        };

        this.$iframe = this.$el.find('iframe');
        this.$iframe.attr("src", this.get_url());
    },
    on_editor_loaded: function (EditorBar) {
        var self = this;
        this.editor = EditorBar;
        this.document = this.$iframe.contents()[0];
                
        var $fullscreen = $('<span class="btn btn-primary" style="margin: 5px;padding: 1px; position: fixed; top: 0; right: 0; z-index: 2000;"><span class="o_fullscreen fa fa-arrows-alt" style="color: white;margin: 3px 5px;"></span></span>');
        var $nav = $("#website-top-navbar", this.document).append($fullscreen);

        $fullscreen.on('click', function () {
            $("body").toggleClass("o_form_FieldTextHtml_fullscreen");
            self.$iframe.css('height', $("body").hasClass('o_form_FieldTextHtml_fullscreen') ? (document.body.clientHeight - self.$iframe.offset().top) + 'px' : '');
        });
        $("body").on('click', function (event) {
            if ($("body").hasClass('o_form_FieldTextHtml_fullscreen')) {
                $("body").removeClass("o_form_FieldTextHtml_fullscreen");
                self.$iframe.css('height', '');
                event.preventDefault();
                event.stopPropagation();
            }
        });

        this.$content = $("#wrapwrap .o_editable:first", this.document);

        function resize() {
            self.$iframe.css("height", Math.max(300,10+self.$content.height()+parseInt(self.$content.parent().css("margin-top")))+"px");
        }
        resize();

        this.dirty = false;
        this.editor.rte.on('change', this, function() {
            self.dirty = true;
            self.trigger('changed_value');
            resize();
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
        if (this.editor && this.editor.snippets && this.dirty) {
            this.editor.snippets.clean_for_save();
            this.internal_set_value( this.$content.prop('innerHTML') );
            this.dirty = false;
        }
        return this.get('value');
    }
});

})();