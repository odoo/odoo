odoo.define('mail.messaging.entity.AttachmentViewer', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function AttachmentViewerFactory({ Entity }) {

    class AttachmentViewer extends Entity {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         * @param {mail.messaging.entity.Attachment} [data.attachment]
         * @param {mail.messaging.entity.Attachment[]} [data.attachments]
         */
        _update(data) {
            const {
                /**
                 * Angle of the image. Changes when the user rotates it.
                 */
                angle = this.angle || 0,
                attachment,
                attachments,
                /**
                 * Determine whether the image is loading or not. Useful to diplay
                 * a spinner when loading image initially.
                 */
                isImageLoading = this.isImageLoading || false,
                /**
                 * Scale size of the image. Changes when user zooms in/out.
                 */
                scale = this.scale || 1,
            } = data;

            if (!this.attachment && attachment) {
                this.link({ attachment });
            }
            if (!this.attachments && attachments) {
                this.link({ attachments });
            }

           this._write({
                angle,
                isImageLoading,
                scale,
            });
        }

    }

    Object.assign(AttachmentViewer, {
        relations: Object.assign({}, Entity.relations, {
            attachment: {
                inverse: 'activeInAttachmentViewer',
                to: 'Attachment',
                type: 'many2one',
            },
            attachments: {
                inverse: 'attachmentViewer',
                to: 'Attachment',
                type: 'many2many',
            },
            messaging: {
                inverse: 'attachmentViewer',
                to: 'Messaging',
                type: 'one2one',
            },
        }),
    });

    return AttachmentViewer;
}

registerNewEntity('AttachmentViewer', AttachmentViewerFactory);

});
