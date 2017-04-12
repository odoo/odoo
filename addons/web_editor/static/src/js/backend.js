odoo.define('web_editor.backend', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var session = require('web.session');
var field_registry = require('web.field_registry');

var QWeb = core.qweb;


/**
 * FieldTextHtml Widget
 * Intended for FieldText widgets meant to display HTML content. This
 * widget will instantiate an iframe with the editor summernote improved by odoo
 */
var FieldTextHtml = AbstractField.extend({
    template: 'web_editor.FieldTextHtml',
    supportedFieldTypes: ['html'],
    start: function () {
        var self = this;

        this.callback = _.uniqueId('FieldTextHtml_');
        window.odoo[this.callback+"_editor"] = function (EditorBar) {
            setTimeout(function () {
                self.on_editor_loaded(EditorBar);
            },0);
        };
        window.odoo[this.callback+"_content"] = function () {
            self.on_content_loaded();
        };
        window.odoo[this.callback+"_updown"] = null;
        window.odoo[this.callback+"_downup"] = function (value) {
            self.set_value(value);
            self.resize();
        };

        // init jqery objects
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();

        this.$iframe.css('min-height', 'calc(100vh - 360px)');

        // init resize
        this.resize = function resize() {
            if (self.mode === 'edit') {
                if ($("body").hasClass("o_form_FieldTextHtml_fullscreen")) {
                    self.$iframe.css('height', (document.body.clientHeight - self.$iframe.offset().top) + 'px');
                } else {
                    self.$iframe.css("height", (self.$body.find("#oe_snippets").length ? 500 : 300) + "px");
                }
            }
        };
        $(window).on('resize', this.resize);

        this.old_initialize_content();
        var def = this._super.apply(this, arguments);
        // this.$translate.remove();
        // this.$translate = $();
        return def;
    },
    get_url: function (_attr) {
        var src = this.nodeOptions.editor_url || "/mass_mailing/field/email_template";
        var k;
        var datarecord = this.recordData;
        var attr = {
            'model': this.model,
            'field': this.name,
            'res_id': datarecord.id || '',
            'callback': this.callback
        };
        _attr = _attr || {};

        if (this.nodeOptions['style-inline']) {
            attr.inline_mode = 1;
        }
        if (this.nodeOptions.snippets) {
            attr.snippets = this.nodeOptions.snippets;
        }
        if (this.nodeOptions.template) {
            attr.template = this.nodeOptions.template;
        }
        if (this. mode === "edit") {
            attr.enable_editor = 1;
        }
        if (this.field.translate) {
            attr.translatable = 1;
        }
        if (session.debug) {
            attr.debug = session.debug;
        }

        attr.lang = attr.enable_editor ? 'en_US' : this.getSession().user_context.lang;

        for (k in _attr) {
            attr[k] = _attr[k];
        }

        if (src.indexOf('?') === -1) {
            src += "?";
        }

        for (k in attr) {
            if (attr[k] !== null) {
                src += "&"+k+"="+(_.isBoolean(attr[k]) ? +attr[k] : attr[k]);
            }
        }

        // delete datarecord[this.name];
        src += "&datarecord="+ encodeURIComponent(JSON.stringify(datarecord));
        return src;
    },
    old_initialize_content: function () {
        this.$el.closest('.modal-body').css('max-height', 'none');
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();
        this.editor = false;
        window.odoo[this.callback+"_updown"] = null;
        this.$iframe.attr("src", this.get_url());
    },
    on_content_loaded: function () {
        var self = this;
        this.document = this.$iframe.contents()[0];
        this.$body = $("body", this.document);
        this.$content = this.$body.find("#editable_area");
        // this._toggle_label();
        this.lang = this.$iframe.attr('src').match(/[?&]lang=([^&]+)/);
        this.lang = this.lang ? this.lang[1] : session.user_context.lang;
        this._dirty_flag = false;
        this.render();
        setTimeout(function () {
            self.trigger_up('perform_model_rpc', {
                model: 'res.lang',
                method: 'search_read',
                args: [
                    [['code', '!=', 'en_US']],
                    ["name", "code"]
                ],
                on_success: function (res) {
                    self.languages = res;
                    self.add_button();
                    setTimeout(self.resize,0);
                }
            });
        }, 0);
    },
    on_editor_loaded: function (EditorBar) {
        var self = this;
        this.editor = EditorBar;
        if (this.value && window.odoo[self.callback+"_updown"] && !(this.$content.html()||"").length) {
            this.render();
        }
        setTimeout(function () {
            setTimeout(self.resize,0);
        }, 0);
    },
    add_button: function () {
        var self = this;
        var $to = this.$body.find("#web_editor-top-edit, #wrapwrap").first();

        $(QWeb.render('FieldTextHtml.translate', {'widget': this}))
            .appendTo($to)
            .on('change', 'select', function () {
                var lang = $(this).val();
                var edit = self. mode === "edit";
                var trans = lang !== 'en_US';
                self.$iframe.attr("src", self.get_url({
                    'edit_translations': edit && trans,
                    'enable_editor': edit && !trans,
                    'lang': lang
                }));
            });

        $(QWeb.render('web_editor.FieldTextHtml.fullscreen'))
            .appendTo($to)
            .on('click', '.o_fullscreen', function () {
                $("body").toggleClass("o_form_FieldTextHtml_fullscreen");
                var full = $("body").hasClass("o_form_FieldTextHtml_fullscreen");
                self.$iframe.parents().toggleClass('o_form_fullscreen_ancestor', full);
                $(window).trigger("resize"); // induce a resize() call and let other backend elements know (the navbar extra items management relies on this)
            });

        this.$body.on('click', '[data-action="cancel"]', function (event) {
            event.preventDefault();
            self.old_initialize_content();
        });
    },
    render: function () {
        if (this.lang !== session.user_context.lang || this.$iframe.attr('src').match(/[?&]edit_translations=1/)) {
            return;
        }
        var value = (this.value || "").replace(/^<p[^>]*>(\s*|<br\/?>)<\/p>$/, '');
        if (!this.$content) {
            return;
        }
        if (this.mode === "edit") {
            if(window.odoo[this.callback+"_updown"]) {
                // FIXME
                // window.odoo[this.callback+"_updown"](value, this.view.get_fields_values(), this.name);
                this.resize();
            }
        } else {
            this.$content.html(value);
            if (this.$iframe[0].contentWindow) {
                this.$iframe.css("height", (this.$body.height()+20) + "px");
            }
        }
    },
    has_no_value: function () {
        return this.value === false || !this.$content.html() || !this.$content.html().match(/\S/);
    },
    // FIXME: not sure what this is supposed to do that is still relevant now
    // commit_value: function () {
    //     if (this.lang !== 'en_US' && this.$body.find('.o_dirty').length) {
    //         this.internal_set_value( this.view.datarecord[this.name] );
    //          this._dirty_flag = false;
    //          return this.editor.save();
    //      } else if (this._dirty_flag && this.editor && this.editor.buildingBlock) {
    //          this.editor.buildingBlock.clean_for_save();
    //          this.internal_set_value( this.$content.html() );
    //      }
    // },
    destroy: function () {
        $(window).off('resize', this.resize);
        delete window.odoo[this.callback+"_editor"];
        delete window.odoo[this.callback+"_content"];
        delete window.odoo[this.callback+"_updown"];
        delete window.odoo[this.callback+"_downup"];
    }
});

field_registry
    .add('html', AbstractField) // TODO
    .add('html_frame', FieldTextHtml);

return {
    FieldTextHtmlSimple: AbstractField,
    FieldTextHtml: FieldTextHtml,
};

});
