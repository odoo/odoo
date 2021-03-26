/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one } from '@mail/model/model_field';

function factory(dependencies) {

    class AttachmentViewer extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close the attachment viewer by closing its linked dialog.
         */
        close() {
            const dialog = this.env.models['mail.dialog'].find(dialog => dialog.record === this);
            if (dialog) {
                dialog.delete();
            }
        }
    }

    AttachmentViewer.fields = {
        /**
         * Angle of the image. Changes when the user rotates it.
         */
        angle: attr({
            default: 0,
        }),
        attachment: many2one('mail.attachment'),
        attachments: many2many('mail.attachment', {
            inverse: 'attachmentViewer',
        }),
        /**
         * Determine whether the image is loading or not. Useful to diplay
         * a spinner when loading image initially.
         */
        isImageLoading: attr({
            default: false,
        }),
        /**
         * Scale size of the image. Changes when user zooms in/out.
         */
        scale: attr({
            default: 1,
        }),
    };

    AttachmentViewer.modelName = 'mail.attachment_viewer';

    return AttachmentViewer;
}

registerNewModel('mail.attachment_viewer', factory);
