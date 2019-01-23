odoo.define('mail.AttachmentBox', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var DocumentViewer = require('mail.DocumentViewer');

var QWeb = core.qweb;

var AttachmentBox = Widget.extend({
    template: 'mail.chatter.AttachmentBox',
    events: {
        "click .o_attachment_download": "_onAttachmentDownload",
        "click .o_attachment_view": "_onAttachmentView",
    },
    /**
     * @override
     * @param {string} record.model
     * @param {Number} record.res_id
     */
    init: function (parent, record) {
        this._super.apply(this, arguments);
        this.currentResID = record.res_id;
        this.currentResModel = record.model;
        this.attachmentIDs = {};
        this.imageList = {};
        this.otherList = {};
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var domain = [
            ['res_id', '=', this.currentResID],
            ['res_model', '=', this.currentResModel],
        ];
        return $.when(this._super.apply(this, arguments), this._rpc({
            model: 'ir.attachment',
            method: 'search_read',
            domain: domain,
            fields: ['id', 'name', 'datas_fname', 'mimetype'],
        }).then(function (result) {
            self.attachmentIDs = result;
            _.each(result, function (attachment) {
                attachment.url = '/web/content/' + attachment.id + '?download=true';
                // required for compatibility with the chatter templates.
                attachment.filename = attachment.datas_fname || 'unnamed';
            });
            var sortedAttachments = _.partition(result, function (att) {
                return att.mimetype && att.mimetype.split('/')[0] === 'image';
            });
            self.imageList = sortedAttachments[0];
            self.otherList = sortedAttachments[1];
        }));
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
});

return AttachmentBox;

});
