odoo.define('mail.component.AttachmentBox', function (require) {
'use strict';

const AttachmentList = require('mail.component.AttachmentList');
const DropZone = require('mail.component.DropZone');
const FileUploader = require('mail.component.FileUploader');
const useDragVisibleDropZone = require('mail.hooks.useDragVisibleDropZone');

const { Component } = owl;
const { useDispatch, useRef, useStore } = owl.hooks;


class AttachmentBox extends Component {

    /**
     * @param {...any} args
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        this.storeDispatch = useDispatch();
        this.storeProps = useStore((state, props) => {
            const thread = state.threads[props.threadLocalId];
            return {
                attachmentLocalIds: thread ? thread.attachmentLocalIds : []
            };
        });
        /**
         * Reference of the file uploader.
         * Useful to programmatically prompts the browser file uploader.
         */
        this._fileUploaderRef = useRef('fileUploader');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get an object which is passed to FileUploader component to be used when
     * creating attachment.
     *
     * @return {Object}
     */
    get newAttachmentExtraData() {
        return {
            threadLocalIds: [this.props.threadLocalId],
        };
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickAdd(ev) {
        this._fileUploaderRef.comp.openBrowserFileUploader();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {FileList} ev.detail.files
     */
    async _onDropZoneFilesDropped(ev) {
        await this._fileUploaderRef.comp.uploadFiles(ev.detail.files);
        this.isDropZoneVisible.value = false;
    }
}

AttachmentBox.components = { AttachmentList, DropZone, FileUploader };

AttachmentBox.props = {
    threadLocalId: String,
};

AttachmentBox.template = 'mail.component.AttachmentBox';

return AttachmentBox;

});
