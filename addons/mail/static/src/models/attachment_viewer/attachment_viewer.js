odoo.define('mail/static/src/models/attachment_viewer/attachment_viewer.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class AttachmentViewer extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close the attachment viewer by closing its linked dialog.
         */
        close() {
            const dialog = this.env.models['mail.dialog'].find(dialog => dialog.__mfield_record(this) === this);
            if (dialog) {
                dialog.delete();
            }
        }
    }

    AttachmentViewer.fields = {
        /**
         * Angle of the image. Changes when the user rotates it.
         */
        __mfield_angle: attr({
            default: 0,
        }),
        __mfield_attachment: many2one('mail.attachment'),
        __mfield_attachments: many2many('mail.attachment', {
            inverse: '__mfield_attachmentViewer',
        }),
        /**
         * Determine whether the image is loading or not. Useful to diplay
         * a spinner when loading image initially.
         */
        __mfield_isImageLoading: attr({
            default: false,
        }),
        /**
         * Scale size of the image. Changes when user zooms in/out.
         */
        __mfield_scale: attr({
            default: 1,
        }),
    };

    AttachmentViewer.modelName = 'mail.attachment_viewer';

    return AttachmentViewer;
}

registerNewModel('mail.attachment_viewer', factory);

});
