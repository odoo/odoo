/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'DropZoneView',
    identifyingFields: [['attachmentBoxViewOwner', 'composerViewOwner']],
    recordMethods: {
        /**
         * Prevents default (from the template) in order to receive the drop event.
         * The drop effect cursor works only when set on dragover.
         *
         * @param {DragEvent} ev
         */
        onDragover(ev) {
            ev.preventDefault();
            ev.dataTransfer.dropEffect = 'copy';
        },
    },
    fields: {
        attachmentBoxViewOwner: one('AttachmentBoxView', {
            inverse: 'dropZoneView',
            readonly: true,
        }),
        composerViewOwner: one('ComposerView', {
            inverse: 'dropZoneView',
            readonly: true,
        }),
    },
});
