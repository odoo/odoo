/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentDeleteConfirmView',
    identifyingFields: ['dialogOwner'],
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
            await this.attachment.remove();
            if (this.chatter && this.chatter.component) {
                this.chatter.component.trigger('o-attachments-changed');
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
            return _.str.sprintf(
                this.env._t(`Do you really want to delete "%s"?`),
                owl.utils.escape(this.attachment.displayName)
            );
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChatter() {
            if (
                this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm &&
                this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.chatter
            ) {
                return replace(this.dialogOwner.attachmentCardOwnerAsAttachmentDeleteConfirm.attachmentList.chatter);
            }
            if (
                this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm &&
                this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.chatter
            ) {
                return replace(this.dialogOwner.attachmentImageOwnerAsAttachmentDeleteConfirm.attachmentList.chatter);
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTitle() {
            return this.env._t("Confirmation");
        },
    },
    fields: {
        attachment: one('Attachment', {
            compute: '_computeAttachment',
        }),
        body: attr({
            compute: '_computeBody',
        }),
        chatter: one('Chatter', {
            compute: '_computeChatter',
        }),
        component: attr(),
        dialogOwner: one('Dialog', {
            readonly: true,
            required: true,
            inverse: 'attachmentDeleteConfirmView',
        }),
        title: attr({
            compute: '_computeTitle',
        }),
    },
});
