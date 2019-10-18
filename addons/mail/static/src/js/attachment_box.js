odoo.define('mail.AttachmentBox', function (require) {
"use strict";

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
});

return AttachmentBox;

});
