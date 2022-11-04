/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { attr, clear, one, registerModel } from '@mail/model';

registerModel({
    name: 'AttachmentBoxView',
    template: 'mail.AttachmentBoxView',
    templateGetter: 'attachmentBoxView',
    componentSetup() {
        useComponentToModel({ fieldName: 'component' });
    },
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
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one('AttachmentList', { inverse: 'attachmentBoxViewOwner',
            compute() {
                return (this.chatter.thread && this.chatter.thread.allAttachments.length > 0)
                    ? {}
                    : clear();
            },
        }),
        chatter: one('Chatter', { identifying: true, inverse: 'attachmentBoxView' }),
        /**
         * States the OWL component displaying this attachment box.
         */
        component: attr(),
        fileUploader: one('FileUploader', { default: {}, inverse: 'attachmentBoxView', readonly: true, required: true }),
    },
});
