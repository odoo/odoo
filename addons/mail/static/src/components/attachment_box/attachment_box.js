/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';

const { Component } = owl;

export class AttachmentBox extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.isDropZoneVisible = useDragVisibleDropZone();
        useComponentToModel({ fieldName: 'component', modelName: 'AttachmentBoxView' });
        this._onDropZoneFilesDropped = this._onDropZoneFilesDropped.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentBoxView|undefined}
     */
    get attachmentBoxView() {
        return this.messaging && this.messaging.models['AttachmentBoxView'].get(this.props.localId);
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
        await this.attachmentBoxView.fileUploader.uploadFiles(detail.files);
        this.isDropZoneVisible.value = false;
    }

}

Object.assign(AttachmentBox, {
    props: { localId: String },
    template: 'mail.AttachmentBox',
});

registerMessagingComponent(AttachmentBox);
