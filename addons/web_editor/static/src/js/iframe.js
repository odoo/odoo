odoo.define('web_editor.iframe', function (require) {
'use strict';

var editor = require('web_editor.editor');
var translator = require('web_editor.translate');
var rte = require('web_editor.rte');
var snippet_editor = require('web_editor.snippet.editor');
var summernote = require('web_editor.rte.summernote');
var dom = summernote.core.dom;
var pluginEvents = summernote.pluginEvents;

window.top.odoo[callback+"_updown"] = function (value, fields_values, field_name) {
    var se = snippet_editor.instance;
    var $editable = $("#editable_area");
    if(value !== se.get_codesource()) {
        if ($('body').hasClass('editor_enable')) {
            if (value !== fields_values[field_name]) {
                rte.history.recordUndo($editable);
            }
            se.make_active(false);
        }
        
        if (!$editable.hasClass('codeview')) {
            $('.note-popover button[data-name="codeview"]').click();
        }
        $('textarea.codesource').val(value).data('indexOfnit', value);
        $('.note-popover button[data-name="codeview"]').click();

        if ($('body').hasClass('editor_enable') && value !== fields_values[field_name]) {
            $editable.trigger("content_changed");
        }
    }
};

editor.Class.include({
    start: function () {
        this.on('rte:start', this, function () {
            this.$('form').hide();

            if (window.top.odoo[callback+"_editor"]) {
                window.top.odoo[callback+"_editor"](this);
            }

            var $editable = $("#editable_area");
            setTimeout(function () {
                $($editable.find("*").filter(function () {return !this.children.length;}).first()[0] || $editable)
                    .focusIn().trigger("mousedown").trigger("keyup");
            },0);

            $editable.on('content_changed', this, function () {
                if (window.top.odoo[callback+"_downup"]) {
                    window.top.odoo[callback+"_downup"]($editable.prop('innerHTML'));
                }
            });
        });

        this.on("snippets:ready", this, function () {
            $(window.top).trigger("resize");
        });

        return this._super();
    },
});

snippet_editor.Class.include({
    start: function () {
        // overwrite dom.html for codeview
        var self = this;
        var _html = dom.html;
        dom.html = function ($dom, prettifyHtml) {
            if (prettifyHtml) {
                self.clean_for_save();
            }
            return _html($dom, prettifyHtml);
        };

        var _codeview = pluginEvents.codeview;
        pluginEvents.codeview = function (event, editor, layoutInfo) {
            self.make_active(false);
            _codeview(event, editor, layoutInfo);
            self.$el.toggle(!$("#editable_area").hasClass('codeview'));
        };

        return this._super();
    },
    get_codesource: function () {
        return $("#editable_area").data('codesource')();
    },
    _get_snippet_url: function () {
        return snippets_url;
    }
});

rte.Class.include({
    config: function ($editable) {
        var config = this._super($editable);
        if ($.deparam($.param.querystring()).debug !== undefined) {
            config.airPopover.splice(7, 0, ['view', ['codeview']]);
        }
        return config;
    },
    onEnableEditableArea: function () {
        var $editable = $("#editable_area");
        if ($editable.data('content') != null) {
            $editable.html('');
            $('.note-popover button[data-name="codeview"]').click();
            $('textarea.codesource').val($editable.data('content'));
            $editable.data('content', null);
            $('.note-popover button[data-name="codeview"]').click();
        }
    }
});

translator.Class.include({
    start: function () {
        var res = this._super();
        $('button[data-action=save]').hide();
        if (window.top.odoo[callback+"_editor"]) {
            window.top.odoo[callback+"_editor"](this);
        }
        return res;
    }
});

});
