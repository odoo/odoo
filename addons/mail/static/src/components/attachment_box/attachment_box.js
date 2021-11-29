/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { useComponentRefToModel } from '@mail/component_hooks/use_component_ref_to_model/use_component_ref_to_model';

const { Component } = owl;

export class AttachmentBox extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.isDropZoneVisible = useDragVisibleDropZone();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.attachment_box_view', propNameAsRecordLocalId: 'attachmentBoxViewLocalId' });
        useComponentRefToModel({ fieldName: 'fileUploader', modelName: 'mail.attachment_box_view', propNameAsRecordLocalId: 'attachmentBoxViewLocalId', refName: 'fileUploader' });
        this._onDropZoneFilesDropped = this._onDropZoneFilesDropped.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachement_box_view|undefined}
     */
    get attachmentBoxView() {
        return this.messaging && this.messaging.models['mail.attachment_box_view'].get(this.props.attachmentBoxViewLocalId);
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
        if (!this.refs.fileUploader) {
            return;
        }
        await this.refs.fileUploader.uploadFiles(detail.files);
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
