odoo.define('mail.component.DropZone', function (require) {
'use strict';

class DropZone extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.id = _.uniqueId('o_dropZone_');
        this.state = owl.useState({
            isDraggingInside: false,
        });
        /**
         * Counts how many drag enter/leave happened on self and children. This
         * ensures the drop effect stays active when dragging over a child.
         */
        this._dragCount = 0;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns whether the given node is self or a children of self.
     *
     * @param {Node} node
     * @return {boolean}
     */
    contains(node) {
        return this.el.contains(node);
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
     * @return {boolean}
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
     * Shows a visual drop effect when dragging inside the dropzone.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragenter(ev) {
        // TODO SEB is this effect working?
        ev.dataTransfer.dropEffect = 'copy';
        if (this._dragCount === 0) {
            this.state.isDraggingInside = true;
        }
        this._dragCount++;
    }

    /**
     * Hides the visual drop effect when dragging outside the dropzone.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragleave(ev) {
        this._dragCount--;
        if (this._dragCount === 0) {
            this.state.isDraggingInside = false;
        }
    }

    /**
     * Prevents default (from the template) in order to receive the drop event.
     *
     * @private
     */
    _onDragover() {}

    /**
     * Triggers the `o-dropzone-files-dropped` event when new files are dropped
     * on the dropzone, and then removes the visual drop effect.
     *
     * The parents should handle this event to process the files as they wish,
     * such as uploading them.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDrop(ev) {
        if (this._isDragSourceExternalFile(ev.dataTransfer)) {
            this.trigger('o-dropzone-files-dropped', {
                files: ev.dataTransfer.files,
            });
        }
        this.state.isDraggingInside = false;
    }

}

DropZone.template = 'mail.component.DropZone';

return DropZone;

});
