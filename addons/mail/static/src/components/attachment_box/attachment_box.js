odoo.define('mail/static/src/components/attachment_box/attachment_box.js', function (require) {
'use strict';

const components = {
    AttachmentList: require('mail/static/src/components/attachment_list/attachment_list.js'),
    DropZone: require('mail/static/src/components/drop_zone/drop_zone.js'),
    FileUploader: require('mail/static/src/components/file_uploader/file_uploader.js'),
};
const useDragVisibleDropZone = require('mail/static/src/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

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
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                attachments: thread
                    ? thread.allAttachments.map(attachment => attachment.__state)
                    : [],
                thread: thread ? thread.__state : undefined,
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
            originThread: [['link', this.thread]],
        };
    }

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onAttachmentCreated(ev) {
        // FIXME Could be changed by spying attachments count (task-2252858)
        this.trigger('o-attachments-changed');
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onAttachmentRemoved(ev) {
        // FIXME Could be changed by spying attachments count (task-2252858)
        this.trigger('o-attachments-changed');
    }

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
    template: 'mail.AttachmentBox',
});

return AttachmentBox;

});
