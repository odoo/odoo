/** @odoo-module **/

import useDragVisibleDropZone from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import AttachmentList from '@mail/components/attachment_list/attachment_list';
import DropZone from '@mail/components/drop_zone/drop_zone';
import FileUploader from '@mail/components/file_uploader/file_uploader';
import { link } from '@mail/model/model_field_command';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = {AttachmentList, DropZone, FileUploader};

class AttachmentBox extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                thread,
                threadAllAttachments: thread ? thread.allAttachments : [],
                threadId: thread && thread.id,
                threadModel: thread && thread.model,
            };
        }, {
            compareDepth: {
                threadAllAttachments: 1,
            },
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
            originThread: link(this.thread),
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

export default AttachmentBox;

