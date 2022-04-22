/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'DropZoneView',
    identifyingFields: [['attachmentBoxViewOwner', 'composerViewOwner']],
    recordMethods: {
        /**
         * Trigger callback 'props.onDropzoneFilesDropped' with event when new files are dropped
         * on the dropzone, and then removes the visual drop effect.
         *
         * The parents should handle this event to process the files as they wish,
         * such as uploading them.
         *
         * @param {DragEvent} ev
         */
        async onDrop(ev) {
            if (!this.exists()) {
                return;
            }
            ev.preventDefault();
            this.update({ isDraggingInside: false });
            if (this._isDragSourceExternalFile(ev.dataTransfer)) {
                if (this.attachmentBoxViewOwner) {
                    await this.attachmentBoxViewOwner.fileUploader.uploadFiles(ev.dataTransfer.files);
                }
                if (this.composerViewOwner) {
                    await this.composerViewOwner.fileUploader.uploadFiles(ev.dataTransfer.files);
                }
            }
        },
        /**
         * Making sure that dragging content is external files.
         * Ignoring other content dragging like text.
         *
         * @private
         * @param {DataTransfer} dataTransfer
         * @returns {boolean}
         */
        _isDragSourceExternalFile(dataTransfer) {
            const dragDataType = dataTransfer.types;
            if (dragDataType.constructor === window.DOMStringList) {
                return dragDataType.contains('Files');
            }
            if (dragDataType.constructor === Array) {
                return dragDataType.includes('Files');
            }
            return false;
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
