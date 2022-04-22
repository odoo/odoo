/** @odoo-module **/

import { decrement } from '@mail/model/model_field_command';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DropZone extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DropZoneView}
     */
    get dropZoneView() {
        return this.messaging && this.messaging.models['DropZoneView'].get(this.props.localId);
    }

    /**
     * Returns whether the given node is self or a children of self.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        return Boolean(this.root.el && this.root.el.contains(node));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Hides the visual drop effect when dragging outside the dropzone.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragleave(ev) {
        if (!this.dropZoneView) {
            return;
        }
        this.dropZoneView.update({ dragCount: decrement() });
        if (this.dropZoneView.dragCount === 0) {
            this.dropZoneView.update({ isDraggingInside: false });
        }
    }

    /**
     * Prevents default (from the template) in order to receive the drop event.
     * The drop effect cursor works only when set on dragover.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragover(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = 'copy';
    }

    /**
     * Trigger callback 'props.onDropzoneFilesDropped' with event when new files are dropped
     * on the dropzone, and then removes the visual drop effect.
     *
     * The parents should handle this event to process the files as they wish,
     * such as uploading them.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDrop(ev) {
        if (!this.dropZoneView) {
            return;
        }
        ev.preventDefault();
        if (this._isDragSourceExternalFile(ev.dataTransfer)) {
            if (this.props.onDropzoneFilesDropped) {
                this.props.onDropzoneFilesDropped({
                    files: ev.dataTransfer.files,
                });
            }
        }
        this.dropZoneView.update({ isDraggingInside: false });
    }

}

Object.assign(DropZone, {
    props: {
        localId: String,
        onDropzoneFilesDropped: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.DropZone',
});

registerMessagingComponent(DropZone);
