/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { decrement, increment } from '@mail/model/model_field_command';

registerModel({
    name: 'DropZoneView',
    identifyingMode: 'xor',
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
        /**
         * Hides the visual drop effect when dragging outside the dropzone.
         *
         * @param {DragEvent} ev
         */
        onDragleave(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ dragCount: decrement() });
            if (this.dragCount === 0) {
                this.update({ isDraggingInside: false });
            }
        },
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
                const files = ev.dataTransfer.files;
                if (this.chatterOwner) {
                    const chatter = this.chatterOwner;
                    if (chatter.isTemporary) {
                        const saved = await chatter.doSaveRecord();
                        if (!saved) {
                            return;
                        }
                    }
                    await chatter.fileUploader.uploadFiles(files);
                    return;
                }
                if (this.composerViewOwner) {
                    await this.composerViewOwner.fileUploader.uploadFiles(files);
                    return;
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
        chatterOwner: one('Chatter', {
            identifying: true,
            inverse: 'dropZoneView',
        }),
        composerViewOwner: one('ComposerView', {
            identifying: true,
            inverse: 'dropZoneView',
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
