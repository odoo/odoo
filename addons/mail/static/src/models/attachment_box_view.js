/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentBoxView',
    identifyingFields: ['chatter'],
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
                ? insertAndReplace()
                : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDropZoneView() {
            if (this.useDragVisibleDropZone.isVisible) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        /**
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one('AttachmentList', {
            compute: '_computeAttachmentList',
            inverse: 'attachmentBoxViewOwner',
            readonly: true,
        }),
        chatter: one('Chatter', {
            inverse: 'attachmentBoxView',
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL component displaying this attachment box.
         */
        component: attr(),
        dropZoneView: one('DropZoneView', {
            compute: '_computeDropZoneView',
            inverse: 'attachmentBoxViewOwner',
        }),
        fileUploader: one('FileUploader', {
            default: insertAndReplace(),
            inverse: 'attachmentBoxView',
            readonly: true,
            required: true,
        }),
        useDragVisibleDropZone: one('UseDragVisibleDropZone', {
            default: insertAndReplace(),
            inverse: 'attachmentBoxViewOwner',
            readonly: true,
            required: true,
        }),
    },
});
