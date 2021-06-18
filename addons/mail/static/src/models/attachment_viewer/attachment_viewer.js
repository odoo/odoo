/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one } from '@mail/model/model_field';
import { link } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

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
         * Handle onclick on next button
         *
         * @param {MouseEvent} ev
         */
        onClickNext(ev) {
            markEventHandled(ev, 'attachmentViewer.clickNext');
            this._next();
        }

        /**
         * Handle onclick on previous button
         *
         * @param {MouseEvent} ev
         */
        onClickPrevious(ev) {
            markEventHandled(ev, 'attachmentViewer.clickPrevious');
            this._previous();
        }

        /**
         * Handle keydown even inside the attachment viewer.
         *
         * @param {MouseEvent} ev
         * @param {String} direction - arrow direction (possible value: next, previous).
         */
        onKeydown(ev, direction) {
            if (direction === 'next') {
                this._next();
            }
            if (direction === 'previous') {
                this._previous();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _next() {
            const index = this.attachments.findIndex(attachment => attachment === this.attachment);
            const nextIndex = (index + 1) % this.attachments.length;
            this.update({ attachment: link(this.attachments[nextIndex]) });
        }

        /**
         * @private
         */
        _previous() {
            const index = this.attachments.findIndex(attachment => attachment === this.attachment);
            const nextIndex = index === 0 ? this.attachments.length - 1 : index - 1;
            this.update({ attachment: link(this.attachments[nextIndex]) });
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
