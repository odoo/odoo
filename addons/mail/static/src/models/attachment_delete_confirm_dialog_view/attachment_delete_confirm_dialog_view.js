/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

registerModel({
    name: 'AttachmentDeleteConfirmDialogView',
    identifyingFields: ['attachment'],
    recordMethods: {
        _computeBody() {
            return _.str.sprintf(
                this.env._t(`Do you really want to delete "%s"?`),
                owl.utils.escape(this.attachment.displayName)
            );
        },
        _computeTitle() {
            return this.env._t("Confirmation");
        },
        /**
         * @private
         */
        onClickCancel() {
            if (!this.dialogRef) {
                return;
            }
            this.dialogRef.comp._close();
        },
        /**
         * @private
         */
        onClickOk() {
            if (!this.dialogRef) {
                return;
            }
            this.dialogRef.comp._close();
            for (const attachmentList of this.attachment.attachmentLists) {
                if (attachmentList.chatter && attachmentList.chatter.attachmentBoxView) {
                    attachmentList.chatter.attachmentBoxView.onAttachmentRemoved();
                }
            }
            this.attachment.remove();
        },
    },
    fields: {
        attachment: one2one('Attachment', {
            inverse: 'attachmentDeleteConfirmDialogView',
            required: true,
            readonly: true,
        }),
        body: attr({
            compute: '_computeBody',
        }),
        dialogRef: attr(),
        title: attr({
            compute: '_computeTitle',
        }),
    },
});
