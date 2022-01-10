/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentBoxView',
    identifyingFields: ['chatter'],
    recordMethods: {
        /**
         * Handles attachment removed event.
         */
        onAttachmentRemoved() {
            // FIXME Could be changed by spying attachments count (task-2252858)
            this.component.trigger('o-attachments-changed');
        },
        /**
         * Handles click on the "add attachment" button.
         */
        onClickAddAttachment() {
            this.fileUploaderView.openBrowserFileUploader();
        },
    },
    fields: {
        chatter: one2one('Chatter', {
            inverse: 'attachmentBoxView',
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL component displaying this attachment box.
         */
        component: attr(),
        fileUploaderView: one2one('FileUploaderView', {
            default: insertAndReplace(),
            inverse: 'attachmentBoxView',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
