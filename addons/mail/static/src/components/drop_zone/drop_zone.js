/** @odoo-module **/

import { decrement, increment } from '@mail/model/model_field_command';
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
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Shows a visual drop effect when dragging inside the dropzone.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragenter(ev) {
        if (!this.dropZoneView) {
            return;
        }
        ev.preventDefault();
        if (this.dropZoneView.dragCount === 0) {
            this.dropZoneView.update({ isDraggingInside: true });
        }
        this.dropZoneView.update({ dragCount: increment() });
    }

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
