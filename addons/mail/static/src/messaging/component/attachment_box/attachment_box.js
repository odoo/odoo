odoo.define('mail.messaging.component.AttachmentBox', function (require) {
'use strict';

const components = {
    AttachmentList: require('mail.messaging.component.AttachmentList'),
    DropZone: require('mail.messaging.component.DropZone'),
    FileUploader: require('mail.messaging.component.FileUploader'),
};
const useDragVisibleDropZone = require('mail.messaging.component_hook.useDragVisibleDropZone');
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;
const { useRef } = owl.hooks;

class AttachmentBox extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        useStore(props => {
            const thread = this.env.entities.Thread.get(props.threadLocalId);
            return {
                attachments: thread ? thread.allAttachments : [],
                thread,
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
     * @returns {Object}
     */
    get newAttachmentExtraData() {
        return {
            res_id: this.thread.id,
            res_model: this.thread.model,
        };
    }

    /**
     * @returns {mail.messaging.entity.Thread|undefined}
     */
    get thread() {
        return this.env.entities.Thread.get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickAdd(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._fileUploaderRef.comp.openBrowserFileUploader();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {FileList} ev.detail.files
     */
    async _onDropZoneFilesDropped(ev) {
        ev.stopPropagation();
        await this._fileUploaderRef.comp.uploadFiles(ev.detail.files);
        this.isDropZoneVisible.value = false;
    }

}

Object.assign(AttachmentBox, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.messaging.component.AttachmentBox',
});

return AttachmentBox;

});
