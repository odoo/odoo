/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';
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
            if (chatter && chatter.exists() && chatter.hasParentReloadOnAttachmentsChanged) {
                chatter.reloadParentView();
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachment() {
            if (this.dialogOwner && this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm) {
                return replace(this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachment);
            }
            if (this.dialogOwner && this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm) {
                return replace(this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachment);
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeBody() {
            return sprintf(this.env._t(`Do you really want to delete "%s"?`), this.attachment.displayName);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChatter() {
            if (
                this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm &&
                this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner &&
                this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter
            ) {
                return replace(this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter);
            }
            if (
                this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm &&
                this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner &&
                this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter
            ) {
                return replace(this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.attachmentBoxViewOwner.chatter);
            }
            return clear();
        },
    },
    fields: {
        attachment: one('Attachment', {
            compute: '_computeAttachment',
            readonly: true,
            required: true,
        }),
        body: attr({
            compute: '_computeBody',
        }),
        chatter: one('Chatter', {
            compute: '_computeChatter',
        }),
        component: attr(),
        dialogOwner: one('Dialog', {
            identifying: true,
            inverse: 'attachmentDeleteConfirmView',
            readonly: true,
            required: true,
        }),
    },
});
