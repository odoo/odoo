odoo.define('web_editor.backend', function (require) {
'use strict';

var core = require('web.core');
var session = require('web.session');
var Model = require('web.DataModel');
var common = require('web.form_common');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var summernote = require('web_editor.summernote');
var transcoder = require('web_editor.transcoder');

var QWeb = core.qweb;
var _t = core._t;

/**
 * FieldTextHtml Widget
 * Intended for FieldText widgets meant to display HTML content. This
 * widget will instantiate an iframe with the editor summernote improved by odoo
 */

var widget = common.AbstractField.extend(common.ReinitializeFieldMixin);

var FieldTextHtmlSimple = widget.extend({
    template: 'web_editor.FieldTextHtmlSimple',
    _config: function () {
        var self = this;
        var config = {
            'focus': false,
            'height': 180,
            'toolbar': [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', ['link', 'picture']],
                ['history', ['undo', 'redo']]
            ],
            'prettifyHtml': false,
            'styleWithSpan': false,
            'inlinemedia': ['p'],
            'lang': "odoo",
            'onChange': function (value) {
                self.internal_set_value(value);
                self.trigger('changed_value');
            }
        };
        if (session.debug) {
            config.toolbar.splice(7, 0, ['view', ['codeview']]);
        }
        return config;
    },
    start: function () {
        var def = this._super.apply(this, arguments);
        this.$translate.remove();
        this.$translate = $();
        // Triggers a mouseup to refresh the editor toolbar
        this.$content.trigger('mouseup');
        return def;
    },
    initialize_content: function () {
        var self = this;
        this.$textarea = this.$("textarea").val(this.get('value') || "<p><br/></p>");
        this.$content = $();

        if (this.get("effective_readonly")) {
            if (this.options['style-inline']) {
                var $iframe = $('<iframe class="o_readonly"/>');
                this.$textarea.hide().after($iframe);
                var load = function () {
                    self.$content = $($iframe.contents()[0]).find("body");
                    self.$content.html(self.text_to_html(self.get('value')));
                    self.resize();
                };
                setTimeout(load);
                $iframe.on('load', load);
            } else {
                this.$content = $('<div class="o_readonly"/>');
                this.$textarea.hide().after(this.$content);
            }
        } else {
            this.$textarea.summernote(this._config());

            if (this.field.translate && this.view) {
                $(QWeb.render('web_editor.FieldTextHtml.button.translate', {'widget': this}))
                    .appendTo(this.$('.note-toolbar'))
                    .on('click', this.on_translate);
            }

            var reset = _.bind(this.reset_history, this);
            this.view.on('load_record', this, reset);
            setTimeout(reset, 0);

            this.$content = this.$('.note-editable:first');
            if (this.options['style-inline']) {
                transcoder.style_to_class(this.$content);
            }
        }

        $(".oe-view-manager-content").on("scroll", function () {
            $('.o_table_handler').remove();
        });
        this._super();
    },
    reset_history: function () {
        var history = this.$content.data('NoteHistory');
        if (history) {
            history.reset();
            self.$('.note-toolbar').find('button[data-event="undo"]').attr('disabled', true);
        }
    },
    text_to_html: function (text) {
        var value = text || "";
        try {
            $(text)[0].innerHTML;
            return text;
        } catch (e) {
            if (value.match(/^\s*$/)) {
                value = '<p><br/></p>';
            } else {
                value = "<p>"+value.split(/<br\/?>/).join("<br/></p><p>")+"</p>";
                value = value.replace(/<p><\/p>/g, '').replace('<p><p>', '<p>').replace('<p><p ', '<p ').replace('</p></p>', '</p>');
            }
        }
        return value;
    },
    focus: function() {
        if (!(!this.get("effective_readonly") && this.$textarea)) {
            return false;
        }
        // on IE an error may occur when creating range on not displayed element
        try {
            return this.$textarea.focusInEnd();
        } catch (e) {
            return this.$textarea.focus();
        }
    },
    resize: function() {
        this.$('> iframe.o_readonly').css('height', '0px').css('height', Math.max(30, Math.min(this.$content[0] ? this.$content[0].scrollHeight : 0, 500)) + 'px');
    },
    render_value: function () {
        var value = this.get('value');
        this.$textarea.val(value || '');
        this.$content.html(this.text_to_html(value));
        if (this.get("effective_readonly")) {
            this.resize();
        } else {
            transcoder.style_to_class(this.$content);
        }
        if (this.$content.is(document.activeElement)) {
            this.focus();
        }
        var history = this.$content.data('NoteHistory');
        if (history && history.recordUndo()) {
            this.$('.note-toolbar').find('button[data-event="undo"]').attr('disabled', false);
        }
    },
    is_false: function () {
        return !this.get('value') || this.get('value') === "<p><br/></p>" || !this.get('value').match(/\S/);
    },
    commit_value: function () {
        /* Switch to WYSIWYG mode if currently in code view */
        if (session.debug) {
            var layoutInfo = this.$textarea.data('layoutInfo');
            $.summernote.pluginEvents.codeview(undefined, undefined, layoutInfo, false);
        }
        if (this.options['style-inline']) {
            transcoder.class_to_style(this.$content);
            transcoder.font_to_img(this.$content);
        }
        this.internal_set_value(this.$content.html());
    },
    destroy_content: function () {
        $(".oe-view-manager-content").off("scroll");
        this.$textarea.destroy();
        this._super();
    }
});

var FieldTextHtml = widget.extend({
    template: 'web_editor.FieldTextHtml',
    willStart: function () {
        var self = this;
        return new Model('res.lang').call("search_read", [[['code', '!=', 'en_US']], ["name", "code"]]).then(function (res) {
            self.languages = res;
        });
    },
    start: function () {
        var self = this;

        this.callback = _.uniqueId('FieldTextHtml_');
        window.odoo[this.callback+"_editor"] = function (EditorBar) {
            setTimeout(function () {
                self.on_editor_loaded(EditorBar);
            },0);
        };
        window.odoo[this.callback+"_content"] = function (EditorBar) {
            self.on_content_loaded();
        };
        window.odoo[this.callback+"_updown"] = null;
        window.odoo[this.callback+"_downup"] = function (value) {
            self.internal_set_value(value);
            self.trigger('changed_value');
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
            if (self.get('effective_readonly')) { return; }
            if ($("body").hasClass("o_form_FieldTextHtml_fullscreen")) {
                self.$iframe.css('height', (document.body.clientHeight - self.$iframe.offset().top) + 'px');
            } else {
                self.$iframe.css("height", (self.$body.find("#oe_snippets").length ? 500 : 300) + "px");
            }
        };
        $(window).on('resize', this.resize);

        var def = this._super.apply(this, arguments);
        this.$translate.remove();
        this.$translate = $();
        return def;
    },
    get_datarecord: function() {
        return this.view.get_fields_values();
    },
    get_url: function (_attr) {
        var src = this.options.editor_url || "/web_editor/field/html";
        var datarecord = this.get_datarecord();

        var attr = {
            'model': this.view.model,
            'field': this.name,
            'res_id': datarecord.id || '',
            'callback': this.callback
        };
        _attr = _attr || {};

        if (this.options['style-inline']) {
            attr.inline_mode = 1;
        }
        if (this.options.snippets) {
            attr.snippets = this.options.snippets;
        }
        if (this.options.template) {
            attr.template = this.options.template;
        }
        if (!this.get("effective_readonly")) {
            attr.enable_editor = 1;
        }
        if (this.field.translate) {
            attr.translatable = 1;
        }
        if (session.debug) {
            attr.debug = session.debug;
        }

        attr.lang = attr.enable_editor ? 'en_US' : this.session.user_context.lang;

        for (var k in _attr) {
            attr[k] = _attr[k];
        }

        if (src.indexOf('?') === -1) {
            src += "?";
        }

        for (var k in attr) {
            if (attr[k] !== null) {
                src += "&"+k+"="+(_.isBoolean(attr[k]) ? +attr[k] : attr[k]);
            }
        }

        delete datarecord[this.name];
        src += "&datarecord="+ encodeURIComponent(JSON.stringify(datarecord));
        return src;
    },
    initialize_content: function () {
        var self = this;
        this.$el.closest('.modal-body').css('max-height', 'none');
        this.$iframe = this.$el.find('iframe');
        this.document = null;
        this.$body = $();
        this.$content = $();
        this.editor = false;
        window.odoo[this.callback+"_updown"] = null;
        this.$iframe.attr("src", this.get_url());
        this.view.on("load_record", this, function(r){
            if (!self.$body.find('.o_dirty').length){
                var url = self.get_url();
                if(url !== self.$iframe.attr("src")){
                    self.$iframe.attr("src", url);
                }
            }
        });
    },
    on_content_loaded: function () {
        var self = this;
        this.document = this.$iframe.contents()[0];
        this.$body = $("body", this.document);
        this.$content = this.$body.find("#editable_area");
        this._toggle_label();
        this.lang = this.$iframe.attr('src').match(/[?&]lang=([^&]+)/);
        this.lang = this.lang ? this.lang[1] : this.view.dataset.context.lang;
        this._dirty_flag = false;
        this.render_value();
        setTimeout(function () {
            self.add_button();
            setTimeout(self.resize,0);
        }, 0);
    },
    on_editor_loaded: function (EditorBar) {
        var self = this;
        this.editor = EditorBar;
        if (this.get('value') && window.odoo[self.callback+"_updown"] && !(this.$content.html()||"").length) {
            this.render_value();
        }
        setTimeout(function () {
            setTimeout(self.resize,0);
        }, 0);
    },
    add_button: function () {
        var self = this;
        var $to = this.$body.find("#web_editor-top-edit, #wrapwrap").first();

        $(QWeb.render('web_editor.FieldTextHtml.translate', {'widget': this}))
            .appendTo($to)
            .on('change', 'select', function () {
                var lang = $(this).val();
                var edit = !self.get("effective_readonly");
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
            self.initialize_content();
        });
    },
    render_value: function () {
        if (this.$iframe.attr('src').match(/[?&]edit_translations=1/)) {
            return;
        }
        // ONLY HAVE THIS IN 9.0 AND SAAS-11
        var is_editor_onchange = this.get('value') === '<p>on_change_model_and_list</p>';
        if (this.lang !== this.view.dataset.context.lang && !is_editor_onchange) {
            return;
        }
        var value = (this.get('value') || "").replace(/^<p[^>]*>(\s*|<br\/?>)<\/p>$/, '');
        if (!this.$content) {
            return;
        }
        if (!this.get("effective_readonly")) {
            if(window.odoo[this.callback+"_updown"]) {
                window.odoo[this.callback+"_updown"](value, this.view.get_fields_values(), this.name);
                this.resize();
            }
        } else {
            this.$content.html(value);
            if (this.$iframe[0].contentWindow) {
                this.$iframe.css("height", (this.$body.height()+20) + "px");
            }
        }
    },
    is_false: function () {
        return this.get('value') === false || !this.$content.html() || !this.$content.html().match(/\S/);
    },
    commit_value: function () {
        if (this.lang !== 'en_US' && this.$body.find('.o_dirty').length) {
            this.internal_set_value( this.view.datarecord[this.name] );
            this._dirty_flag = false;
            return this.editor.save();
        } else if (this._dirty_flag && this.editor && this.editor.buildingBlock) {
            /* Switch to WYSIWYG mode if currently in code view */
            if (session.debug) {
                var layoutInfo = this.editor.rte.editable().data('layoutInfo');
                $.summernote.pluginEvents.codeview(undefined, undefined, layoutInfo, false);
            }
            this.editor.buildingBlock.clean_for_save();
            this.internal_set_value( this.$content.html() );
        }
    },
    destroy: function () {
        $(window).off('resize', this.resize);
        delete window.odoo[this.callback+"_editor"];
        delete window.odoo[this.callback+"_content"];
        delete window.odoo[this.callback+"_updown"];
        delete window.odoo[this.callback+"_downup"];
    }
});

core.form_widget_registry
    .add('html', FieldTextHtmlSimple)
    .add('html_frame', FieldTextHtml);

return {
    FieldTextHtmlSimple: FieldTextHtmlSimple,
    FieldTextHtml: FieldTextHtml,
};

});
