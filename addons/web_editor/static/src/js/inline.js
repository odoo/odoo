odoo.define('web_editor.inline', function (require) {
'use strict';

var editor = require('web_editor.editor');
var rte = require('web_editor.rte');
var widget = require('web_editor.widget');
var transcoder = require('web_editor.transcoder');
var snippet_editor = require('web_editor.snippet.editor');
var summernote = require('web_editor.rte.summernote');
var pluginEvents = summernote.pluginEvents;
var dom = summernote.core.dom;

var _html = dom.html;
dom.html = function ($dom, prettifyHtml) {
    if (prettifyHtml) {
        transcoder.font_to_img($dom);
        transcoder.class_to_style($dom);

        // fix outlook image rendering bug
        _.each(['width', 'height'], function(attribute) {
            $dom.find('img[style*="width"], img[style*="height"]').attr(attribute, function(){
                return $(this)[attribute]();
            }).css(attribute, function(){
                return $(this).get(0).style[attribute] || 'auto';
            });
        });
    }
    return _html($dom, prettifyHtml);
};

var _value = dom.value;
dom.value = function ($dom, stripLinebreaks, $editable) {
    var value = _value($dom, stripLinebreaks);
    if (stripLinebreaks) {
        $editable = $editable || $('<div/>');
        $editable.html(value);
        transcoder.img_to_font($editable);
        transcoder.style_to_class($editable);

        // fix outlook image rendering bug
        $editable.find('img[style*="width"], img[style*="height"]').removeAttr('height width');

        value = $editable.html();
    }
    return value;
};


widget.MediaDialog.include({
    start: function () {
        this._super();
        this.$('[href="#editor-media-video"]').addClass('hidden');
    }
});

editor.Class.include({
    start: function () {
        var self = this;
        if (location.search.indexOf("enable_editor") !== -1) {
            this.on('rte:start', this, function () {
                // move the caret at the end of the text when click after all content
                $("#wrapwrap").on('click', function (event) {
                    if ($(event.target).is("#wrapwrap") || $(event.target).is("#editable_area:empty")) {
                        setTimeout(function () {
                            var node = $("#editable_area *")
                                .filter(function () { return this.textContent.match(/\S|\u00A0/); })
                                .add($("#editable_area"))
                                .last()[0];
                            $.summernote.core.range.create(node, $.summernote.core.dom.nodeLength(node)).select();
                        },0);
                    }
                });
            });
        }
        return this._super.apply(this, arguments);
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