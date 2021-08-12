/** @odoo-module **/

import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { link } from '@mail/model/model_field_command';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;
const { useRef } = owl.hooks;

export class ChatterAttachmentBox extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.isDropZoneVisible = useDragVisibleDropZone();
        useComponentToModel({ fieldName: 'attachementBoxComponent', modelName: 'mail.chatter', propNameAsRecordLocalId: 'chatterLocalId' });
        useRefToModel({ fieldName: 'fileUploaderRef', modelName: 'mail.chatter', propNameAsRecordLocalId: 'chatterLocalId', refName: 'fileUploader' });
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
     * @returns {mail.thread|undefined}
     */
    get chatter() {
        return this.messaging && this.messaging.models['mail.chatter'].get(this.props.chatterLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

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

Object.assign(ChatterAttachmentBox, {
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ChatterAttachmentBox',
});

registerMessagingComponent(ChatterAttachmentBox);
