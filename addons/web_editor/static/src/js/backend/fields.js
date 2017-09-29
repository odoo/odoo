odoo.define('web_editor.backend', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var basic_fields = require('web.basic_fields');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var field_registry = require('web.field_registry');
var SummernoteManager = require('web_editor.rte.summernote');
var transcoder = require('web_editor.transcoder');

var TranslatableFieldMixin = basic_fields.TranslatableFieldMixin;

var QWeb = core.qweb;
var _t = core._t;


/**
 * FieldTextHtmlSimple Widget
 * Intended to display HTML content. This widget uses the summernote editor
 * improved by odoo.
 *
 */
var FieldTextHtmlSimple = basic_fields.DebouncedField.extend(TranslatableFieldMixin, {
    className: 'oe_form_field oe_form_field_html_text',
    supportedFieldTypes: ['html'],

    /**
     * @override
     */
    start: function () {
        new SummernoteManager(this);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Summernote doesn't notify for changes done in code mode. We override
     * commitChanges to manually switch back to normal mode before committing
     * changes, so that the widget is aware of the changes done in code mode.
     *
     * @override
     */
    commitChanges: function () {
        // switch to WYSIWYG mode if currently in code mode to get all changes
        if (config.debug && this.mode === 'edit') {
            var layoutInfo = this.$textarea.data('layoutInfo');
            $.summernote.pluginEvents.codeview(undefined, undefined, layoutInfo, false);
        }
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    isSet: function () {
        return this.value && this.value !== "<p><br/></p>" && this.value.match(/\S/);
    },
    /**
     * Do not re-render this field if it was the origin of the onchange call.
     *
     * @override
     */
    reset: function (record, event) {
        this._reset(record, event);
        if (!event || event.target !== this) {
            if (this.mode === 'edit') {
                this.$content.html(this._textToHtml(this.value));
            } else {
                this._renderReadonly();
            }
        }
        return $.when();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Object} the summernote configuration
     */
    _getSummernoteConfig: function () {
        var summernoteConfig = {
            focus: false,
            height: 180,
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', ['link', 'picture']],
                ['history', ['undo', 'redo']]
            ],
            prettifyHtml: false,
            styleWithSpan: false,
            inlinemedia: ['p'],
            lang: "odoo",
            onChange: this._doDebouncedAction.bind(this),
        };
        if (config.debug) {
            summernoteConfig.toolbar.splice(7, 0, ['view', ['codeview']]);
        }
        return summernoteConfig;
    },
    /**
     * @override
     * @private
     */
    _getValue: function () {
        if (this.nodeOptions['style-inline']) {
            transcoder.classToStyle(this.$content);
            transcoder.fontToImg(this.$content);
        }
        return this.$content.html();
    },
    /**
     * @override
     * @private
     */
    _renderEdit: function () {
        this.$textarea = $('<textarea>');
        this.$textarea.appendTo(this.$el);
        this.$textarea.summernote(this._getSummernoteConfig());
        this.$content = this.$('.note-editable:first');
        this.$content.html(this._textToHtml(this.value));
        // trigger a mouseup to refresh the editor toolbar
        this.$content.trigger('mouseup');
        if (this.nodeOptions['style-inline']) {
            transcoder.styleToClass(this.$content);
        }
        // reset the history (otherwise clicking on undo before editing the
        // value will empty the editor)
        var history = this.$content.data('NoteHistory');
        if (history) {
            history.reset();
        }
        this.$('.note-toolbar').append(this._renderTranslateButton());
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        var self = this;
        this.$el.empty();
        if (this.nodeOptions['style-inline']) {
            var $iframe = $('<iframe class="o_readonly"/>');
            $iframe.on('load', function () {
                self.$content = $($iframe.contents()[0]).find("body");
                self.$content.html(self._textToHtml(self.value));
                self._resize();
            });
            $iframe.appendTo(this.$el);
        } else {
            this.$content = $('<div class="o_readonly"/>');
            this.$content.html(this._textToHtml(this.value));
            this.$content.appendTo(this.$el);
        }
    },
    /**
     * Sets the height of the iframe.
     *
     * @private
     */
    _resize: function () {
        var height = this.$content[0] ? this.$content[0].scrollHeight : 0;
        this.$('iframe').css('height', Math.max(30, Math.min(height, 500)) + 'px');
    },
    /**
     * @private
     * @param {string} text
     * @returns {string} the text converted to html
     */
    _textToHtml: function (text) {
        var value = text || "";
        try {
            $(text)[0].innerHTML; // crashes if text isn't html
        } catch (e) {
            if (value.match(/^\s*$/)) {
                value = '<p><br/></p>';
            } else {
                value = "<p>" + value.split(/<br\/?>/).join("<br/></p><p>") + "</p>";
                value = value
                            .replace(/<p><\/p>/g, '')
                            .replace('<p><p>', '<p>')
                            .replace('<p><p ', '<p ')
                            .replace('</p></p>', '</p>');
            }
        }
        return value;
    },
    /**
     * @override
     * @private
     * @returns {jQueryElement}
     */
    _renderTranslateButton: function () {
        if (_t.database.multi_lang && this.field.translate && this.res_id) {
            return $(QWeb.render('web_editor.FieldTextHtml.button.translate', {widget: this}))
                .on('click', this._onTranslate.bind(this));
        }
        return $();
    },

});

var FieldTextHtml = AbstractField.extend({
    template: 'web_editor.FieldTextHtml',
    supportedFieldTypes: ['html'],

    start: function () {
        var self = this;

        this.loaded = false;
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
        window.odoo[this.callback+"_downup"] = function () {
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
                if ($("body").hasClass("o_field_widgetTextHtml_fullscreen")) {
                    self.$iframe.css('height', (document.body.clientHeight - self.$iframe.offset().top) + 'px');
                } else {
                    self.$iframe.css("height", (self.$body.find("#oe_snippets").length ? 500 : 300) + "px");
                }
            }
        };
        $(window).on('resize', this.resize);

        this.old_initialize_content();
        var def = this._super.apply(this, arguments);
        return def;
    },
    getDatarecord: function () {
        return this.recordData;
    },
    get_url: function (_attr) {
        var src = this.nodeOptions.editor_url || "/mass_mailing/field/email_template";
        var k;
        var datarecord = this.getDatarecord();
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
        if (this.mode === "edit") {
            attr.enable_editor = 1;
        }
        if (session.debug) {
            attr.debug = session.debug;
        }

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
        this.render();
        this.add_button();
        this.loaded = true;
        setTimeout(self.resize, 0);
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

        $(QWeb.render('web_editor.FieldTextHtml.fullscreen'))
            .appendTo($to)
            .on('click', '.o_fullscreen', function () {
                $("body").toggleClass("o_field_widgetTextHtml_fullscreen");
                var full = $("body").hasClass("o_field_widgetTextHtml_fullscreen");
                self.$iframe.parents().toggleClass('o_form_fullscreen_ancestor', full);
                $(window).trigger("resize"); // induce a resize() call and let other backend elements know (the navbar extra items management relies on this)
            });

        this.$body.on('click', '[data-action="cancel"]', function (event) {
            event.preventDefault();
            self.old_initialize_content();
        });
    },
    render: function () {
        var value = (this.value || "").replace(/^<p[^>]*>(\s*|<br\/?>)<\/p>$/, '');
        if (!this.$content) {
            return;
        }
        if (this.mode === "edit") {
            if (window.odoo[this.callback+"_updown"]) {
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
    destroy: function () {
        $(window).off('resize', this.resize);
        delete window.odoo[this.callback+"_editor"];
        delete window.odoo[this.callback+"_content"];
        delete window.odoo[this.callback+"_updown"];
        delete window.odoo[this.callback+"_downup"];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    commitChanges: function () {
        if (!this.loaded || this.mode === 'readonly') {
            return;
        }
        // switch to WYSIWYG mode if currently in code mode to get all changes
        if (config.debug && this.mode === 'edit' && this.editor.rte) {
            var layoutInfo = this.editor.rte.editable().data('layoutInfo');
            $.summernote.pluginEvents.codeview(undefined, undefined, layoutInfo, false);
        }
        this.editor.snippetsMenu.cleanForSave();
        this._setValue(this.$content.html());
        return this._super.apply(this, arguments);
    },
});

field_registry
    .add('html', FieldTextHtmlSimple)
    .add('html_frame', FieldTextHtml);

return {
    FieldTextHtmlSimple: FieldTextHtmlSimple,
    FieldTextHtml: FieldTextHtml,
};
});
