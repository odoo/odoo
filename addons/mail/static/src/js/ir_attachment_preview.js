odoo.define('mail.ir_attachment_preview', function (require) {

var KanbanRenderer = require('web.KanbanRenderer');
var KanbanRecord = require('web.KanbanRecord');
var DocumentViewer = require('mail.DocumentViewer');

KanbanRecord.include({
    events: _.extend({}, KanbanRecord.prototype.events, {
        'click .o_document_preview .o_attachment_preview': '_openAttachmentPreview',
        'click .o_download_content, .o_overlay_download': '_downloadContent',
    }),
    /**
     * @private
     */
    _openAttachmentPreview: function (event) {
        event.stopPropagation();
        var activeAttachmentID = $(event.currentTarget).closest('.oe_kanban_global_click').data().record.recordData.id;
        this.trigger_up('attachmentsPreview',{activeAttachment: activeAttachmentID});
    },
    /**
     * @private
     */
    _downloadContent: function (event) {
        /* disable propagation for preventing clicks on kanban containing images */
        event.stopPropagation();
    },
});

KanbanRenderer.include({
    custom_events: _.extend({}, KanbanRenderer.prototype.custom_events, {
        attachmentsPreview : '_attachmentsPreview',
    }),
    /**
     * Open preview of attachment using document_viewer widget
     * @private
     */
    _attachmentsPreview: function (event) {
        var activeAttachmentID = event.data.activeAttachment;
        var isGrouped = this.state.groupedBy.length;
        if (!isGrouped) {
            var attachments = _.map(this.state.data, function (el) { return el.data; });
        } else {
            var attachments = [];
            _.each(this.state.data, function (group) {
                _.each(group.data, function (data) {
                    attachments.push(data.data);
                });
            });
        }

        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, attachments, activeAttachmentID);
            attachmentViewer.prependTo($('body'));
        }
    },

});

});
