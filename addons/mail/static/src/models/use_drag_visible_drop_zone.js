/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { decrement, increment } from '@mail/model/model_field_command';

registerModel({
    name: 'UseDragVisibleDropZone',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            document.addEventListener('dragenter', this._onDragenterListener, true);
            document.addEventListener('dragleave', this._onDragleaveListener, true);
            document.addEventListener('drop', this._onDropListener);

            // Thoses Events prevent the browser to open or download the file if
            // it's dropped outside of the dropzone
            window.addEventListener('dragover', ev => ev.preventDefault());
            window.addEventListener('drop', ev => ev.preventDefault());
        },
        _willDelete() {
            document.removeEventListener('dragenter', this._onDragenterListener, true);
            document.removeEventListener('dragleave', this._onDragleaveListener, true);
            document.removeEventListener('drop', this._onDropListener);

            window.removeEventListener('dragover', ev => ev.preventDefault());
            window.removeEventListener('drop', ev => ev.preventDefault());
        },
    },
    recordMethods: {
        /**
         * Shows the dropzone when entering the browser window, to let the user know
         * where they can drop their file.
         * Avoids changing state when entering inner dropzones.
         *
         * @private
         * @param {DragEvent} ev
         */
        _onDragenterListener(ev) {
            if (
                this.dragCount === 0 &&
                ev.dataTransfer &&
                ev.dataTransfer.types.includes('Files')
            ) {
                this.update({ isVisible: true });
            }
            this.update({ dragCount: increment() });
        },
        /**
         * @private
         * @param {DragEvent} ev
         */
        _onDragleaveListener(ev) {
            this.update({ dragCount: decrement() });
            if (this.dragCount === 0) {
                this.update({ isVisible: false });
            }
        },
        /**
         * @private
         * @param {DragEvent} ev
         */
        _onDropListener(ev) {
            this.update({
                dragCount: 0,
                isVisible: false,
            });
        },
    },
    fields: {
        chatterOwner: one('Chatter', {
            identifying: true,
            inverse: 'useDragVisibleDropZone',
        }),
        composerViewOwner: one('ComposerView', {
            identifying: true,
            inverse: 'useDragVisibleDropZone',
        }),
        /**
         * Counts how many drag enter/leave happened globally. This is the only
         * way to know if a file has been dragged out of the browser window.
         */
        dragCount: attr({
            default: 0
        }),
        /**
         * Determine whether the drop zone should be visible or not.
         */
        isVisible: attr({
            default: false,
        }),
    },
});
