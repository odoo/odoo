odoo.define('mail/static/src/models/attachment_viewer/attachment_viewer.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field.js');

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
        /**
         * save rotated image if it was rotated in attachmentviewer.
         *
         * @param {object} rotatedAttachments
         */
        async saveRotateImage(rotatedAttachments) {
            const rotatedAttachmentIds = Object.keys(rotatedAttachments).map(Number);
            await this.env.services.rpc({
                model: 'ir.attachment',
                method: 'rotate_image',
                args: [rotatedAttachmentIds],
                kwargs: { angles: Object.values(rotatedAttachments) },
            });
            rotatedAttachmentIds.forEach((id) => {
                const attachment = this.attachments.find((attachment) => attachment.id === id);
                attachment.update({ uuid: _.uniqueId(attachment.id), angle: rotatedAttachments[id] });
            });
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

});
