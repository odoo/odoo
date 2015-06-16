odoo.define('website.backend', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_widgets = require('web.form_widgets'); // required to guarantee that
    // the overrride of fieldtexthtml works

var WidgetWebsiteButton = form_common.AbstractField.extend({
    template: 'WidgetWebsiteButton',
    render_value: function() {
        // Hack to replace false value by unpublished because falsy form fields
        // have classname o_form_field_empty and are hidden
        if (!this.get_value()) {
            this.set_value('unpublished');
        }
        this._super();
        this.$el.toggleClass("published", this.get_value() === true);
        if (this.node.attrs.class) {
            this.$el.addClass(this.node.attrs.class);
        }
    },
});

core.form_widget_registry.add('website_button', WidgetWebsiteButton);

var FieldWidget = form_common.AbstractField.extend(form_common.ReinitializeFieldMixin);


var FieldTextHtmlFrame = FieldWidget.extend({
    template: 'FieldTextHtmlFrame',
    start: function () {
        var self = this;

        this.callback = _.uniqueId('FieldTextHtml_');
        odoo[this.callback+"_editor"] = function (EditorBar) {
            self.on_editor_loaded(EditorBar);
        };
        odoo[this.callback+"_content"] = function () {
            self.on_content_loaded();
        };
        odoo[this.callback+"_downup"] = function (value) {
            self.dirty = true;
            self.internal_set_value(value);
            self.trigger('changed_value');
            self.resize();
        };

        // init jqery objects
        this.$iframe = this.$('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();

        // init resize
        this.resize = function resize() {
            if (self.get('effective_readonly')) {
               $("body").removeClass("o_form_FieldTextHtml_fullscreen");
            }
            if ($("body").hasClass("o_form_FieldTextHtml_fullscreen")) {
                self.$iframe.css('height', $("body").hasClass('o_form_FieldTextHtml_fullscreen') ? (document.body.clientHeight - self.$iframe.offset().top) + 'px' : '');
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
            attr.snippets = this.options.snippets;
        }
        if (!this.get("effective_readonly")) {
            attr.enable_editor = 1;
        }
        if (core.debug) {
            attr.debug = 1;
        }

        for (var k in attr) {
            src += "&"+k+"="+attr[k];
        }

        delete datarecord[this.name];
        src += "&datarecord="+ encodeURIComponent(JSON.stringify(datarecord));

        return src;
    },
    initialize_content: function() {
        if (!this.get("effective_readonly")) {
            this.$iframe = this.$el.find('iframe');
            this.document = null;
            this.$body = $();
            this.$content = $();
            this.dirty = false;
            this.editor = false;
            odoo[this.callback+"_set_value"] = null;
            this.$iframe.attr("src", this.get_url());
        }
    },
    on_content_loaded: function () {
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

        if (this.get('value') && window.odoo[this.callback+"_set_value"] && !(this.$content.prop('innerHTML')||"").length) {
            this.render_value();
        }

        setTimeout(function () {
            var $fullscreen = $('<span class="btn btn-primary" style="margin: 5px;padding: 1px; position: fixed; top: 0; right: 0; z-index: 2000;"><span class="o_fullscreen fa fa-arrows-alt" style="color: white;margin: 3px 5px;"></span></span>');
            $("#website-top-navbar", self.document).append($fullscreen);
            $fullscreen.on('click', function () {
                $("body").toggleClass("o_form_FieldTextHtml_fullscreen");
                self.resize();
            });
            setTimeout(self.resize,0);
        }, 500);
    },
    render_value: function() {
        var value = (this.get('value') || "").replace(/^<p[^>]*>\s*<\/p>$/, '');
        if (!this.get("effective_readonly")) {
            if (!this.$content) {
                return;
            }
            if(window.odoo[this.callback+"_set_value"]) {
                window.odoo[this.callback+"_set_value"](value || '', this.view.get_fields_values(), this.name);
                this.resize();
            }
        } else {
            this.$el.html(value);
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
        $("body").removeClass("o_form_FieldTextHtml_fullscreen");
        $(window).off('resize', self.resize);
        $(window).off('keydown', self.escape);
        delete window.odoo[this.callback+"_content"];
        delete window.odoo[this.callback+"_downup"];
        delete window.odoo[this.callback+"_set_value"];
    }
});

core.form_widget_registry.add('html_frame', FieldTextHtmlFrame);

});
