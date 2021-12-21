/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentBoxView',
    identifyingFields: ['chatter'],
    lifecycleHooks: {
        _created() {
            this.onAttachmentCreated = this.onAttachmentCreated.bind(this);
            this.onAttachmentRemoved = this.onAttachmentRemoved.bind(this);
            this.onClickAddAttachment = this.onClickAddAttachment.bind(this);
        },
    },
    recordMethods: {
        /**
         * Handles attachment created event.
         */
        onAttachmentCreated() {
            // FIXME Could be changed by spying attachments count (task-2252858)
            this.component.trigger('o-attachments-changed');
        },
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
            this.fileUploaderRef.comp.openBrowserFileUploader();
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
        fileUploader: one2one('FileUploader', {
            default: insertAndReplace(),
            inverse: 'attachmentBoxView',
            isCausal: true,
        }),
        /**
         * States the OWL ref of the "fileUploader" of this attachment box.
         */
        fileUploaderRef: attr(),
    },
});
