odoo.define('web_editor.wysiwyg.plugin.dropzone', function (require) {
'use strict';

var core = require('web.core');
var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');
var utils = require('web.utils');

var _t = core._t;
var dom = $.summernote.dom;

var DropzonePlugin = Plugins.dropzone.extend({
    //--------------------------------------------------------------------------
    // Public summernote module API
    //--------------------------------------------------------------------------

    /**
     * Disable Summernote's handling of drop events.
     */
    attachDragAndDropEvent: function () {
        this._super.apply(this, arguments);
        this.$dropzone.off('drop');
        this.$dropzone.on('dragenter', this._onDragenter.bind(this));
        this.$dropzone.on('drop', this._onDrop.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Clean up then drops HTML or plain text into the editor.
     *
     * @private
     * @param {String} html
     * @param {Boolean} textOnly true to allow only dropping plain text
     */
    _dropHTML: function (html, textOnly) {
        this.context.invoke('editor.beforeCommand');

        // Clean up
        var nodes = this.context.invoke('TextPlugin.prepareClipboardData', html);

        // Delete selection
        this.context.invoke('HelperPlugin.deleteSelection');

        // Insert the nodes
        this.context.invoke('TextPlugin.pasteNodes', nodes, textOnly);
        this.context.invoke('HelperPlugin.normalize');
        this.context.invoke('editor.saveRange');

        this.context.invoke('editor.afterCommand');
    },
    /**
     * Drop images into the editor: save them as attachments.
     *
     * @private
     * @param {File[]]} files (images only)
     */
    _dropImages: function (files) {
        var self = this;
        this.context.invoke('editor.beforeCommand');
        var range = this.context.invoke('editor.createRange');

        var spinners = [];
        var images = [];
        var defs = [];
        _.each(files, function (file) {
            // Add spinner
            var spinner = $('<span class="fa fa-spinner fa-spin">').attr('data-filename', file.name)[0];
            self.context.invoke('editor.hidePopover');
            if (range.sc.tagName) {
                if (range.so >= dom.nodeLength(range.sc)) {
                    $(range.sc).append(spinner);
                } else {
                    $(range.sc.childNodes[range.so]).before(spinner);
                }
            } else {
                range.sc.splitText(range.so);
                $(range.sc).after(spinner);
            }
            spinners.push(spinner);

            // save images as attachments
            var def = new Promise(function (resolve) {
                // Get image's Base64 string
                utils.getDataURLFromFile(file).then(function (result) {
                    self._uploadImage(result, file.name).then(function (attachment) {
                        // Make the HTML
                        var image = self.document.createElement('img');
                        image.setAttribute('style', 'width: 100%;');
                        image.src = '/web/content/' + attachment.id + '/' + attachment.name;
                        image.alt = attachment.name;
                        $(spinner).replaceWith(image);
                        images.push(image);
                        resolve(image);
                        $(image).trigger('dropped');
                    });
                });
            });
            defs.push(def);
        });

        this.trigger_up('drop_images', {
            spinners: spinners,
            promises: defs,
        });

        Promise.all(defs).then(function () {
            var defs = [];
            $(images).each(function () {
                if (!this.height) {
                    var def = new Promise(function (resolve) {
                        $(this).one('load error abort', resolve);
                    });
                    defs.push(def);
                }
            });
            Promise.all(defs).then(function () {
                if (images.length === 1) {
                    range = self.context.invoke('editor.setRange', _.last(images), 0);
                    range.select();
                    self.context.invoke('editor.saveRange');
                    self.context.invoke('editor.afterCommand');
                    self.context.invoke('MediaPlugin.updatePopoverAfterEdit', images[0]);
                } else {
                    self.context.invoke('editor.afterCommand');
                }
            });
        });
    },
    /**
     * Upload an image from its Base64 representation.
     *
     * @private
     * @param {String} imageBase64
     * @param {String} fileName
     * @returns {Promise}
     */
    _uploadImage: function (imageBase64, fileName) {
        var options = {};
        this.trigger_up('getRecordInfo', {
            recordInfo: options,
            type: 'media',
            callback: function (recordInfo) {
                _.defaults(options, recordInfo);
            },
        });

        return this._rpc({
            route: '/web_editor/attachment/add_data',
            params: {
                'data': imageBase64.split(';base64,').pop(),
                'name': fileName,
                'res_id': options.res_id || 0,
                'res_model': options.res_model,
            },
        });
    },
    /**
     * @private
     * @param {JQueryEvent} e
     */
    _onDragenter: function (e) {
        var range = this.context.invoke('editor.createRange');
        if (!this.editable.contains(range.sc)) {
            var node = this.editable;
            if (node && node.firstChild) {
                node = node.firstChild;
            }
            range = this.context.invoke('editor.setRange', node, 0, node, 0);
            range.select();
        }
    },
    /**
     * @private
     * @param {JQueryEvent} e
     */
    _onDrop: function (e) {
        e.preventDefault();

        this.$editor.removeClass('dragover');

        if (this.options.disableDragAndDrop) {
            return;
        }
        var dataTransfer = e.originalEvent.dataTransfer;

        if (!this._canDropHere()) {
            this.context.invoke('HelperPlugin.notify', _t("Not a dropzone"), _t("Dropping is prohibited in this area."));
            return;
        }

        if (dataTransfer.getData('text/html')) {
            this._dropHTML(dataTransfer.getData('text/html'));
            return;
        }
        if (dataTransfer.files.length) {
            var images = [];
            _.each(dataTransfer.files, function (file) {
                if (file.type.indexOf('image') !== -1) {
                    images.push(file);
                }
            });
            if (!images.length || images.length < dataTransfer.files.length) {
                this.context.invoke('HelperPlugin.notify', _t("Unsupported file type"), _t("Images are the only file types that can be dropped."));
            }
            if (images.length) {
                this._dropImages(images);
            }
        }
    },
    /**
     * Return true if dropping is allowed at the current range.
     *
     * @private
     * @returns {Boolean}
     */
    _canDropHere: function () {
        var range = this.context.invoke('editor.createRange');
        return this.options.isEditableNode(range.sc);
    },
});

registry.add('dropzone', DropzonePlugin);

return DropzonePlugin;

});
