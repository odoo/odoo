odoo.define('mail.DragAndDropMixin', function (require) {
"use strict";

/**
 * Mixin for drag and drop file.
 */
const DragAndDropFileMixin = {
    events: {
        'dragover .o_file_drop_zone_container': '_onDragoverFileDropZone',
        'drop .o_file_drop_zone_container': '_onDropFile',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Making sure that dragging content is external files.
     * Ignoring other content draging like text.
     *
     * @private
     * @param {DataTransfer} dataTransfer
     * @returns {boolean}
     */
    _isDragSourceExternalFile(dataTransfer) {
        const DragDataType = dataTransfer.types;
        if (DragDataType.constructor === DOMStringList) {
            return DragDataType.contains('Files');
        }
        if (DragDataType.constructor === Array) {
            return DragDataType.includes('Files');
        }
        return false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Setting drop Effect to copy so when mouse pointer on dropzone
     * cursor icon changed to copy ('+')
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onDragoverFileDropZone(ev) {
        ev.originalEvent.dataTransfer.dropEffect = "copy";
    },
    /**
     * Called when user drop selected files on drop area
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onDropFile(ev) {
        ev.preventDefault();
        $(".o_file_drop_zone_container").addClass("d-none");
        if (this._isDragSourceExternalFile(ev.originalEvent.dataTransfer)) {
            const files = ev.originalEvent.dataTransfer.files;
            this._processAttachmentChange({files: files});
        }
    },
};

return DragAndDropFileMixin;

});
