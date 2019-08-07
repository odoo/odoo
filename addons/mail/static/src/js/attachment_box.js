odoo.define('mail.AttachmentBox', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');

var DocumentViewer = require('mail.DocumentViewer');

var QWeb = core.qweb;
var _t = core._t;

var AttachmentBox = Widget.extend({
    template: 'mail.chatter.AttachmentBox',
    events: {
        "click .o_attachment_download": "_onAttachmentDownload",
        "click .o_attachment_view": "_onAttachmentView",
        "click .o_attachment_delete_cross": "_onDeleteAttachment",
        "click .o_upload_attachments_button": "_onUploadAttachments",
        "change .o_chatter_attachment_form .o_form_binary_form": "_onAddAttachment",
        'dragover .o_attachments_file_drop_zone': '_onFileDragover',
        'drop .o_attachments_file_drop_zone': '_onFileDrop',
    },
    /**
     * @override
     * @param {string} record.model
     * @param {Number} record.res_id
     * @param {Object[]} attachments
     */
    init: function (parent, record, attachments) {
        this._super.apply(this, arguments);
        this.fileuploadId = _.uniqueId('oe_fileupload');
        $(window).on(this.fileuploadId, this._onUploaded.bind(this));
        this.currentResID = record.res_id;
        this.currentResModel = record.model;
        this.attachmentIDs = attachments;
        this.imageList = {};
        this.otherList = {};

        _.each(attachments, function (attachment) {
            // required for compatibility with the chatter templates.
            attachment.url = '/web/content/' + attachment.id + '?download=true';
            attachment.filename = attachment.name || _t('unnamed');
        });
        var sortedAttachments = _.partition(attachments, function (att) {
            return att.mimetype && att.mimetype.split('/')[0] === 'image';
        });
        this.imageList = sortedAttachments[0];
        this.otherList = sortedAttachments[1];
    },
    /**
     * @override
     */
    destroy: function () {
        $(window).off(this.fileuploadId);
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} record
     */
    update: function (record) {
        this.currentResID = record.res_id;
        this.currentResModel = record.model;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Calls controller to upload file, separate method is created
     * to use it in tests to patch it.
     *
     * @param {string} controllerUrl
     * @param {FormData} formData
     */
    _callUploadAttachment: function (controllerUrl, formData) {
        return $.ajax({
            url: controllerUrl,
            type: "POST",
            enctype: 'multipart/form-data',
            processData: false,
            contentType: false,
            data: formData,
            success: (result) => {
                var $el = $(result);
                $.globalEval($el.contents().text());
            }
        });
    },
    /**
     * Making sure that dragging content is external files.
     * Ignoring other content draging like text.
     *
     * @private
     * @param {DataTransfer} dataTransfer
     * @returns {boolean}
     */
    _isDragSourceExternalFile: function (dataTransfer) {
        var DragDataType = dataTransfer.types;
        if (DragDataType.constructor === DOMStringList) {
            return DragDataType.contains('Files');
        }
        if (DragDataType.constructor === Array) {
            return DragDataType.indexOf('Files') !== -1;
        }
        return false;
    },
    /**
     * Upload attachment with drag & drop feature.
     *
     * @private
     * @param {Array<File>} params.files
     */
    _processAttachmentChange: function (files) {
        var self = this;
        var $form = this.$('form.o_form_binary_form');
        var formData = new FormData();
        $form.find("input").each((index, input) => {
            if (input.name != "ufile") {
                formData.append(input.name, input.value);
            }
        });
        _.each(files, (file) => formData.append("ufile", file, file.name));
        self._callUploadAttachment($form.attr("action"), formData);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Method triggered when user click on 'add attachment' and select a file
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onAddAttachment: function (ev) {
        var $input = $(ev.currentTarget).find('input.o_input_file');
        if ($input.val() !== '') {
            var $binaryForm = this.$('form.o_form_binary_form');
            $binaryForm.submit();
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * used to prevent the click from opening the document viewer.
     */
    _onAttachmentDownload: function (ev) {
        ev.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAttachmentView: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var activeAttachmentID = $(ev.currentTarget).data('id');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, this.attachmentIDs, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
    /**
     * Opens File Explorer dialog if all fields are valid and record is saved
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onUploadAttachments: function (ev) {
        this.$('input.o_input_file').click();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDeleteAttachment: function (ev) {
        ev.stopPropagation();
        var $target = $(ev.currentTarget);
        this.trigger_up('delete_attachment', {
            attachmentId: $target.data('id'),
            attachmentName: $target.data('name')
        });
    },
    /**
     * @private
     */
    _onUploaded: function() {
        this.trigger_up('reload_attachment_box');
    },
    /**
     * Setting drop Effect to copy so when mouse pointer on dropzone
     * cursor icon changed to copy ('+')
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onFileDragover: function (ev) {
        ev.originalEvent.dataTransfer.dropEffect = "copy";
    },
    /**
     * Called when user drop selected files on drop area
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onFileDrop: function (ev) {
        ev.preventDefault();
        $(".o_attachments_file_drop_zone").addClass("d-none");
        if (this._isDragSourceExternalFile(ev.originalEvent.dataTransfer)) {
            var files = ev.originalEvent.dataTransfer.files;
            this._processAttachmentChange(files);
        }
    },
});

return AttachmentBox;

});
