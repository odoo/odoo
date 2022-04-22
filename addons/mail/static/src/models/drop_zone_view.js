/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { increment } from '@mail/model/model_field_command';

registerModel({
    name: 'DropZoneView',
    identifyingFields: [['attachmentBoxViewOwner', 'composerViewOwner']],
    recordMethods: {
        /**
         * Shows a visual drop effect when dragging inside the dropzone.
         *
         * @param {DragEvent} ev
         */
        onDragenter(ev) {
            if (!this.exists()) {
                return;
            }
            ev.preventDefault();
            if (this.dragCount === 0) {
                this.update({ isDraggingInside: true });
            }
            this.update({ dragCount: increment() });
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
        /**
         * Counts how many drag enter/leave happened on self and children. This
         * ensures the drop effect stays active when dragging over a child.
         */
        dragCount: attr({
            default: 0,
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
