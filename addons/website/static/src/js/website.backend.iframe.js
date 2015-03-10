odoo.define('website.backend.iframe', ['website.editor', 'website.snippets.editor'], function (require) {
'use strict';

var editor = require('website.editor');
var snippet_editor = require('website.snippets.editor');

window.top.odoo[callback+"_set_value"] = function (value, fields_values) {
    var $editable = $("#wrapwrap .o_editable:first");
    if (value !== $editable.html()) {
        if ($('body').hasClass('editor_enable')) {
            editor.editor_bar.rte.historyRecordUndo($editable);
            editor.editor_bar.snippets.make_active(false);
        }
        $editable.html(value);
    }
};

editor.EditorBar.include({
    start: function () {
        var self = this;
        var res = this._super.apply(this, arguments);
        if (location.search.indexOf("enable_editor") !== -1) {
            this.on('rte:ready', this, function () {
                $("#website-top-edit").hide();
                setTimeout(function () {
                    if (window.top.odoo[callback+"_editor"]) {
                        window.top.odoo[callback+"_editor"](this);
                    }
                }, 0);

                var $editable = $("#wrapwrap .o_editable:first");
                setTimeout(function () {
                    $($editable.find("*").filter(function () {return !this.children.length;}).first()[0] || $editable)
                        .focusIn().trigger("mousedown").trigger("keyup");
                },0);

                this.rte.on('change', this, function () {
                    window.top.odoo[callback+"_downup"]($editable.prop('innerHTML'));
                });


                $(window).on('keydown', function (event) {
                    if(event.keyCode === 27 && $("body", window.top.document).hasClass("o_form_FieldTextHtml_fullscreen")) {
                        $(".o_fullscreen").trigger("click");
                    }
                    $(window).trigger('resize');
                });

            });

            var style = document.createElement("style");
            style.textContent = "#wrapwrap > main > * { margin-top: 50px; }";
            $("head").append(style);

            this.on("snippets:ready", this, function () {
                $(window.top).trigger("resize");
            });

        } else if (window.top.odoo[callback+"_editor"]) {
            window.top.odoo[callback+"_editor"](this);
        }
        return res;
    },
    cancel: function () {
        return;
    },
});

snippet_editor.BuildingBlock.include({
    _get_snippet_url: function () {
        return snippets_url;
    }
});

});
