/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class AttachmentBoxView extends dependencies['mail.model'] {

        _created() {
            this.onAttachmentCreated = this.onAttachmentCreated.bind(this);
            this.onAttachmentRemoved = this.onAttachmentRemoved.bind(this);
            this.onClickAddAttachment = this.onClickAddAttachment.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Handles attachment created event.
         */
        onAttachmentCreated() {
            // FIXME Could be changed by spying attachments count (task-2252858)
            this.component.trigger('o-attachments-changed');
        }

        /**
         * Handles attachment removed event.
         */
        onAttachmentRemoved() {
            // FIXME Could be changed by spying attachments count (task-2252858)
            this.component.trigger('o-attachments-changed');
        }

        /**
         * Handles click on the "add attachment" button.
         */
        onClickAddAttachment() {
            this.fileUploaderRef.comp.openBrowserFileUploader();
        }

    }

    AttachmentBoxView.fields = {
        chatter: one2one('mail.chatter', {
            inverse: 'attachmentBoxView',
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL component displaying this attachment box.
         */
        component: attr(),
        /**
         * States the OWL ref of the "fileUploader" of this attachment box.
         */
        fileUploaderRef: attr(),
    };
    AttachmentBoxView.identifyingFields = ['chatter'];
    AttachmentBoxView.modelName = 'mail.attachment_box_view';

    return AttachmentBoxView;
}

registerNewModel('mail.attachment_box_view', factory);
