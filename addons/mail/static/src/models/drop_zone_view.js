/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'DropZoneView',
    identifyingFields: [['attachmentBoxViewOwner', 'composerViewOwner']],
    fields: {
        attachmentBoxViewOwner: one('AttachmentBoxView', {
            inverse: 'dropZoneView',
            readonly: true,
        }),
        composerViewOwner: one('ComposerView', {
            inverse: 'dropZoneView',
            readonly: true,
        }),
        /**
         * Determines whether the user is dragging files over the dropzone.
         * Useful to provide visual feedback in that case.
         */
        isDraggingInside: attr({
            default: false,
        }),
    },
});
