odoo.define('mail/static/src/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone.js', function (require) {
'use strict';

const { useState, onMounted, onWillUnmount } = owl.hooks;

/**
 * This hook handle the visibility of the dropzone based on drag & drop events.
 * It needs a ref to a dropzone, so you need to specify a t-ref="dropzone" in
 * the template of your component.
 *
 * @returns {Object}
 */
function useDragVisibleDropZone() {
    /**
     * Determine whether the drop zone should be visible or not.
     * Note that this is an observed value, and primitive types such as
     * boolean cannot be observed, hence this is an object with boolean
     * value accessible from `.value`
     */
    const isVisible = useState({ value: false });

    /**
     * Counts how many drag enter/leave happened globally. This is the only
     * way to know if a file has been dragged out of the browser window.
     */
    let dragCount = 0;

    // COMPONENTS HOOKS
    onMounted(() => {
        document.addEventListener('dragenter', _onDragenterListener, true);
        document.addEventListener('dragleave', _onDragleaveListener, true);
        document.addEventListener('drop', _onDropListener, true);

        // Thoses Events prevent the browser to open or download the file if
        // it's dropped outside of the dropzone
        window.addEventListener('dragover', ev => ev.preventDefault());
        window.addEventListener('drop', ev => ev.preventDefault());
    });

    onWillUnmount(() => {
        document.removeEventListener('dragenter', _onDragenterListener, true);
        document.removeEventListener('dragleave', _onDragleaveListener, true);
        document.removeEventListener('drop', _onDropListener, true);

        window.removeEventListener('dragover', ev => ev.preventDefault());
        window.removeEventListener('drop', ev => ev.preventDefault());
    });

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Shows the dropzone when entering the browser window, to let the user know
     * where he can drop its file.
     * Avoids changing state when entering inner dropzones.
     *
     * @private
     * @param {DragEvent} ev
     */
    function _onDragenterListener(ev) {
        if (dragCount === 0) {
            isVisible.value = true;
        }
        dragCount++;
    }

    /**
     * @private
     * @param {DragEvent} ev
     */
    function _onDragleaveListener(ev) {
        dragCount--;
        if (dragCount === 0) {
            isVisible.value = false;
        }
    }

    /**
     * @private
     * @param {DragEvent} ev
     */
    function _onDropListener(ev) {
        dragCount = 0;
        isVisible.value = false;
    }

    return isVisible;
}

return useDragVisibleDropZone;

});
