/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentBoxView',
    recordMethods: {
        /**
         * Handles click on the "add attachment" button.
         */
        onClickAddAttachment() {
            this.fileUploader.openBrowserFileUploader();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentList() {
            return (this.chatter.thread && this.chatter.thread.allAttachments.length > 0)
                ? {}
                : clear();
        },
    },
    fields: {
        /**
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one('AttachmentList', {
            compute: '_computeAttachmentList',
            inverse: 'attachmentBoxViewOwner',
            isCausal: true,
        }),
        chatter: one('Chatter', {
            identifying: true,
            inverse: 'attachmentBoxView',
        }),
        /**
         * States the OWL component displaying this attachment box.
         */
        component: attr(),
        fileUploader: one('FileUploader', {
            default: {},
            inverse: 'attachmentBoxView',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
