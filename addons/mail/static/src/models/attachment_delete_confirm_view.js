/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'AttachmentDeleteConfirmView',
    recordMethods: {
        /**
         * Returns whether the given html element is inside this attachment delete confirm view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        onClickCancel() {
            this.dialogOwner.delete();
        },
        async onClickOk() {
            const chatter = this.chatter;
            await this.attachment.remove();
            if (chatter && chatter.exists() && chatter.shouldReloadParentFromFileChanged) {
                chatter.reloadParentView();
            }
        },
    },
    fields: {
        attachment: one('Attachment', {
            compute() {
                if (this.dialogOwner && this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm) {
                    return this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachment;
                }
                if (this.dialogOwner && this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm) {
                    return this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachment;
                }
                return clear();
            },
            required: true,
        }),
        body: attr({
            compute() {
                return sprintf(this.env._t(`Do you really want to delete "%s"?`), this.attachment.displayName);
            },
        }),
        chatter: one('Chatter', {
            compute() {
                if (
                    this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm &&
                    this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner &&
                    this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter
                ) {
                    return this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter;
                }
                if (
                    this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm &&
                    this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner &&
                    this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter
                ) {
                    return this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter;
                }
                return clear();
            },
        }),
        component: attr(),
        dialogOwner: one('Dialog', {
            identifying: true,
            inverse: 'attachmentDeleteConfirmView',
        }),
    },
});
