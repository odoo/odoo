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
    },
    fields: {
        /**
         * Determines the attachment list view that will be used to display the attachments.
         */
        attachmentListView: one('AttachmentListView', {
            compute() {
                return (this.chatter.thread && this.chatter.thread.allAttachments.length > 0)
                    ? {}
                    : clear();
            },
            inverse: 'attachmentBoxViewOwner',
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
            readonly: true,
            required: true,
        }),
    },
});
