odoo.define('mail/static/src/components/drop_zone/drop_zone.js', function (require) {
'use strict';

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');

const { Component, useState } = owl;

class DropZone extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        this.state = useState({
            /**
             * Determine whether the user is dragging files over the dropzone.
             * Useful to provide visual feedback in that case.
             */
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
     * @returns {boolean}
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
     * Shows a visual drop effect when dragging inside the dropzone.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragenter(ev) {
        ev.preventDefault();
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
        ev.preventDefault();
        if (this._isDragSourceExternalFile(ev.dataTransfer)) {
            this.trigger('o-dropzone-files-dropped', {
                files: ev.dataTransfer.files,
            });
        }
        this.state.isDraggingInside = false;
    }

}

Object.assign(DropZone, {
    props: {},
    template: 'mail.DropZone',
});

return DropZone;

});
