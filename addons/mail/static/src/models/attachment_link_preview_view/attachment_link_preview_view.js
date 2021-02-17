/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

function factory(dependencies) {

    class AttachmentlinkPreviewView extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickUnlink = this.onClickUnlink.bind(this);
            this.onDeleteConfirmDialogClosed = this.onDeleteConfirmDialogClosed.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Handles the click on delete attachment and open the confirm dialog.
         *
         * @param {MouseEvent} ev
         */
        onClickUnlink(ev) {
            if (!this.attachment) {
                return;
            }
            if (this.attachment.composer) {
                this.component.trigger('o-attachment-removed', { attachmentLocalId: this.attachment.localId });
                this.attachment.remove();
            } else {
                this.update({ hasDeleteConfirmDialog: true });
            }
        }

        /**
         * Synchronize the `hasDeleteConfirmDialog` when the dialog is closed.
         */
        onDeleteConfirmDialogClosed() {
            if (!this.exists()) {
                return;
            }
            this.update({ hasDeleteConfirmDialog: false });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {number|FieldCommand}
         */
        _computeHeight() {
            if (!this.attachment) {
                return clear();
            }
            if (this.attachment.composer) {
                return 50;
            }
            return 160;
        }

        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeImageUrl() {
            if (!this.attachment) {
                return clear();
            }
            if (!this.attachment.accessToken && this.attachment.originThread && this.attachment.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.attachment.originThread.id}/image/${this.attachment.id}/${this.width}x${this.height}`;
            }
            const accessToken = this.attachment.accessToken ? `?access_token=${this.attachment.accessToken}` : '';
            return `/web/image/${this.attachment.id}/${this.width}x${this.height}${accessToken}`;
        }

        /**
         * @private
         * @returns {number}
         */
        _computeWidth() {
            if (!this.attachment) {
                return clear();
            }
            return 160;
        }

    }

    AttachmentlinkPreviewView.fields = {
        /**
         * Determines the attachment of this link preview.
         */
        attachment: many2one('mail.attachment', {
            inverse: 'attachmentLinkPreviewsView',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the attachmentList for this link preview.
         */
        attachmentList: many2one('mail.attachment_list', {
            inverse: 'attachmentLinkPreviewsView',
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL component of this attachment image.
         */
        component: attr(),
        /**
         * States the status of the delete confirm dialog (open/closed).
         */
        hasDeleteConfirmDialog: attr({
            default: false,
        }),
        /**
         * Determines the max height of this attachment image in px.
         */
        height: attr({
            compute: '_computeHeight',
            required: true,
        }),
        imageUrl: attr({
            compute: '_computeImageUrl',
        }),
        /**
         * Determines the max width of this attachment image in px.
         */
        width: attr({
            compute: '_computeWidth',
            required: true,
        }),
    };

    AttachmentlinkPreviewView.identifyingFields = ['attachmentList', 'attachment'];
    AttachmentlinkPreviewView.modelName = 'mail.attachment_link_preview_view';

    return AttachmentlinkPreviewView;
}

registerNewModel('mail.attachment_link_preview_view', factory);
