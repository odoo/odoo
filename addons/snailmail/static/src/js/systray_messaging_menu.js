odoo.define('snailmail.systray.MessagingMenu', function (require) {
"use strict";

var MessagingMenu = require('mail.systray.MessagingMenu');

MessagingMenu.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    
    /**
     * Called when clicking on a preview related to a snailmail failure
     *
     * @private
     * @param {$.Element} $target DOM of preview element clicked
     */
    _clickSnailmailFailurePreview: function ($target) {
        var documentID = $target.data('document-id');
        var documentModel = $target.data('document-model');
        if (documentModel && documentID) {
            this._openDocument(documentModel, documentID);
        } else if (documentModel !== 'mail.channel') {
            // preview of mail failures grouped to different document of same model
            this.do_action({
                name: "Snailmail failures",
                type: 'ir.actions.act_window',
                view_mode: 'kanban,list,form',
                views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                target: 'current',
                res_model: documentModel,
                domain: [['message_ids.snailmail_error', '=', true]],
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
   _onClickPreview: function (ev) {
       var $target = $(ev.currentTarget);
       var previewID = $target.data('preview-id');
       
        if (previewID === 'snailmail_failure') {
            this._clickSnailmailFailurePreview($target);
        } else {
            this._super.apply(this, arguments);
        }
   },
    /**
     * @private
     * @override
     */
    _onClickPreviewMarkAsRead: function (ev) {
        ev.stopPropagation();
        var $preview = $(ev.currentTarget).closest('.o_mail_preview');
        var previewID = $preview.data('preview-id');
        if (previewID === 'snailmail_failure') {
            var documentModel = $preview.data('document-model');
            var unreadCounter = $preview.data('unread-counter');
            this.do_action('snailmail.snailmail_letter_cancel_action', {
                additional_context: {
                    default_model: documentModel,
                    unread_counter: unreadCounter
                }
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
