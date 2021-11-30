/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;
const { useRef } = owl.hooks;

export class AttachmentBox extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.isDropZoneVisible = useDragVisibleDropZone();
        /**
         * Reference of the file uploader.
         * Useful to programmatically prompts the browser file uploader.
         */
        this._fileUploaderRef = useRef('fileUploader');
        useComponentToModel({ fieldName: 'component', modelName: 'AttachmentBoxView', propNameAsRecordLocalId: 'attachmentBoxViewLocalId' });
        useRefToModel({ fieldName: 'fileUploaderRef', modelName: 'AttachmentBoxView', propNameAsRecordLocalId: 'attachmentBoxViewLocalId', refName: 'fileUploader' });
        this._onDropZoneFilesDropped = this._onDropZoneFilesDropped.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentBoxView|undefined}
     */
    get attachmentBoxView() {
        return this.messaging && this.messaging.models['AttachmentBoxView'].get(this.props.attachmentBoxViewLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} detail
     * @param {FileList} detail.files
     */
    async _onDropZoneFilesDropped(detail) {
        await this._fileUploaderRef.comp.uploadFiles(detail.files);
        this.isDropZoneVisible.value = false;
    }

}

Object.assign(AttachmentBox, {
    props: {
        attachmentBoxViewLocalId: String,
    },
    template: 'mail.AttachmentBox',
});

registerMessagingComponent(AttachmentBox);
