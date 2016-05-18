odoo.define('web_editor.iframe', function (require) {
'use strict';

var editor = require('web_editor.editor');
var translator = require('web_editor.translate');
var rte = require('web_editor.rte');
var snippet_editor = require('web_editor.snippet.editor');

window.top.odoo[callback+"_updown"] = function (value, fields_values, field_name) {
    var $editable = $("#editable_area");
    if(value !== $editable.prop("innerHTML")) {
        if ($('body').hasClass('editor_enable')) {
            if (value !== fields_values[field_name]) {
                rte.history.recordUndo($editable);
            }
            snippet_editor.instance.make_active(false);
        }
        
        $editable.html(value);

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
    }
});

snippet_editor.Class.include({
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
