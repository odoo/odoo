odoo.define('web_editor.inline', function (require) {
'use strict';

var core = require('web.core');
var editor = require('web_editor.editor');
var rte = require('web_editor.rte');
var weWidgets = require('web_editor.widget');
var transcoder = require('web_editor.transcoder');
var snippet_editor = require('web_editor.snippet.editor');

weWidgets.MediaDialog.include({
    start: function () {
        this.$('[href="#editor-media-video"]').addClass('d-none');
        return this._super.apply(this, arguments);
    },
});

editor.Class.include({
    start: function () {
        if (window.location.search.indexOf('enable_editor') !== -1) {
            this.on('rte:start', this, function () {
                // move the caret at the end of the text when click after all content
                $('#wrapwrap').on('click', function (event) {
                    if ($(event.target).is('#wrapwrap') || $(event.target).is('#editable_area:empty')) {
                        _.defer(function () {
                            var node = $('#editable_area *')
                                .filter(function () { return this.textContent.match(/\S|\u00A0/); })
                                .add($('#editable_area'))
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
        _.defer(function () {
            var $editable = $('#editable_area');
            transcoder.linkImgToAttachmentThumbnail($editable);
            transcoder.imgToFont($editable);
            transcoder.styleToClass($editable);

            // fix outlook image rendering bug
            $editable.find('img[style*="width"], img[style*="height"]').removeAttr('height width');
        });
        return this._super.apply(this, arguments);
    },
    cleanForSave: function () {
        this._super.apply(this, arguments);

        var $editable = $('#editable_area');
        transcoder.attachmentThumbnailToLinkImg($editable);
        transcoder.fontToImg($editable);
        transcoder.classToStyle($editable);

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

var callback = window ? window['callback'] : undefined;
window.top.odoo[callback + '_updown'] = function (value, fields_values) {
    var $editable = $('#editable_area');
    value = value || '';
    if (value.indexOf('on_change_model_and_list') === -1 && value !== $editable.html()) {
        rte.history.recordUndo($editable, null, true);
        core.bus.trigger('deactivate_snippet');

        $editable.html(value);

        transcoder.imgToFont($editable);
        transcoder.styleToClass($editable);

        // fix outlook image rendering bug
        $editable.find('img[style*="width"], img[style*="height"]').removeAttr('height width');
    } else {
        $editable.trigger('content_changed');
    }
};
});
