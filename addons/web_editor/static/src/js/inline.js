odoo.define('web_editor.inline', function (require) {
'use strict';

var editor = require('web_editor.editor');
var rte = require('web_editor.rte');
var widget = require('web_editor.widget');
var transcoder = require('web_editor.transcoder');
var snippet_editor = require('web_editor.snippet.editor');

widget.MediaDialog.include({
    start: function () {
        this._super.apply(this, arguments);
        this.$('[href="#editor-media-video"]').addClass('hidden');
    }
});

editor.Class.include({
    start: function () {
        if (location.search.indexOf("enable_editor") !== -1) {
            this.on('rte:start', this, function () {
                // move the caret at the end of the text when click after all content
                $("#wrapwrap").on('click', function (event) {
                    if ($(event.target).is("#wrapwrap") || $(event.target).is("#editable_area:empty")) {
                        _.defer(function () {
                            var node = $("#editable_area *")
                                .filter(function () { return this.textContent.match(/\S|\u00A0/); })
                                .add($("#editable_area"))
                                .last()[0];
                            $.summernote.core.range.create(node, $.summernote.core.dom.nodeLength(node)).select();
                        });
                    }
                });
            });
        }
        return this._super.apply(this, arguments);
    },
});

snippet_editor.Class.include({
    start: function () {
        this._super.apply(this, arguments);
        setTimeout(function () {
            var $editable = $("#editable_area");
            transcoder.img_to_font($editable);
            transcoder.style_to_class($editable);

            // fix outlook image rendering bug
            $editable.find('img[style*="width"], img[style*="height"]').removeAttr('height width');
        });
    },
    clean_for_save: function () {
        this._super.apply(this, arguments);
        var $editable = $("#editable_area");
        transcoder.font_to_img($editable);
        transcoder.class_to_style($editable);

        // fix outlook image rendering bug
        _.each(['width', 'height'], function (attribute) {
            $editable.find('img[style*="width"], img[style*="height"]').attr(attribute, function () {
                return $(this)[attribute]();
            }).css(attribute, function () {
                return $(this).get(0).style[attribute] || 'auto';
            });
        });
    },
});

window.top.odoo[callback+"_updown"] = function (value, fields_values) {
    var $editable = $("#editable_area");
    value = value || "";
    if (value.indexOf('on_change_model_and_list') === -1 && value !== $editable.html()) {
        rte.history.recordUndo($editable, null, true);
        if (snippet_editor.instance) {
            snippet_editor.instance.make_active(false);
        }

        $editable.html(value);

        transcoder.img_to_font($editable);
        transcoder.style_to_class($editable);

        // fix outlook image rendering bug
        $editable.find('img[style*="width"], img[style*="height"]').removeAttr('height width');
    } else {
        $editable.trigger("content_changed");
    }
};
});
