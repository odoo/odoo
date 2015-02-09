(function () {
    'use strict';

var widgets = openerp.web.form.widgets;
while(!widgets.map.html) {
    widgets = widgets.parent;
}
widgets.map.html = "openerp.web.form.FieldTextHtml";

var widget = openerp.web.form.AbstractField.extend(openerp.web.form.ReinitializeFieldMixin);
openerp.web.form.FieldTextHtml = widget.extend({
    template: 'FieldTextHtml',
    start: function () {
        var self = this;

        this.callback = _.uniqueId('FieldTextHtml_');
        window.openerp[this.callback+"_editor"] = function (EditorBar) {
            self.on_editor_loaded(EditorBar);
        };
        window.openerp[this.callback+"_content"] = function (EditorBar) {
            self.on_content_loaded();
        };
        window.openerp[this.callback+"_updown"] = null;
        window.openerp[this.callback+"_downup"] = function (value) {
            self.dirty = true;
            self.internal_set_value(value);
            self.trigger('changed_value');
            self.resize();
        };

        // init jqery objects
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();

        // init resize
        this.resize = function resize() {
            if ($("body").hasClass("o_form_FieldTextHtml_fullscreen")) {
                self.$iframe.css('height', $("body").hasClass('o_form_FieldTextHtml_fullscreen') ? (document.body.clientHeight - self.$iframe.offset().top) + 'px' : '');
            } else if (self.get('effective_readonly')) {
                var height = 110;
                try {
                    height += self.$body.height();
                    height +=  parseInt(self.$content.parent().css("margin-top"));
                } catch (e) {}
                self.$iframe.css("height", height+"px");
            } else {
                self.$iframe.css("height", (self.$body.find("#oe_snippets").length ? 500 : 300) + "px");
            }
        };
        $(window).on('resize', self.resize);

        return this._super();
    },
    get_url: function () {
        var src = this.options.editor_url ? this.options.editor_url+"?" : "/website/field/html?";
        var datarecord = this.view.get_fields_values();

        var attr = {
            'model': this.view.model,
            'field': this.name,
            'res_id': datarecord.id || '',
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

        delete datarecord[this.name];
        src += "&datarecord="+ encodeURIComponent(JSON.stringify(datarecord));

        return src;
    },
    initialize_content: function() {
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();
        this.dirty = false;
        this.editor = false;
        window.openerp[this.callback+"_set_value"] = function () {};

        this.$iframe.attr("src", this.get_url());
    },
    on_content_loaded: function () {
        var self = this;
        this.document = this.$iframe.contents()[0];
        this.$body = $("body", this.document);
        this.$content = this.$body.find("#wrapwrap .o_editable:first");
        setTimeout(this.resize,0);
    },
    on_editor_loaded: function (EditorBar) {
        var self = this;
        this.editor = EditorBar;

        $("body").on('click', function (event) {
            if ($("body").hasClass('o_form_FieldTextHtml_fullscreen')) {
                $("body").removeClass("o_form_FieldTextHtml_fullscreen");
                self.$iframe.css('height', '');
                event.preventDefault();
                event.stopPropagation();
            }
        });

        setTimeout(function () {
            var $fullscreen = $('<span class="btn btn-primary" style="margin: 5px;padding: 1px; position: fixed; top: 0; right: 0; z-index: 2000;"><span class="o_fullscreen fa fa-arrows-alt" style="color: white;margin: 3px 5px;"></span></span>');
            var $nav = $("#website-top-navbar", self.document).append($fullscreen);
            $fullscreen.on('click', function () {
                $("body").toggleClass("o_form_FieldTextHtml_fullscreen");
                self.resize();
            });
            setTimeout(self.resize,0);
        }, 500);
    },
    render_value: function() {
        if (!this.$content) {
            return;
        }
        if(window.openerp[this.callback+"_set_value"]) {
            window.openerp[this.callback+"_set_value"](this.get('value') || '', this.view.get_fields_values());
            this.resize();
        }
    },
    is_false: function() {
        return this.get('value') === false || this.get('value') === "";
    },
    get_value: function(save_mode) {
        if (save_mode && this.editor && this.editor.snippets && this.dirty) {
            this.editor.snippets.clean_for_save();
            this.internal_set_value( this.$content.prop('innerHTML') );
        }
        return this.get('value');
    },
    destroy: function () {
        $(window).off('resize', self.resize);
        delete window.openerp[this.callback];
        delete window.openerp[this.callback+"_content"];
        delete window.openerp[this.callback+"_updown"];
    }
});

})();