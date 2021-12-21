/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;

export class FileUploader extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'fileInputRef', modelName: 'FileUploader', propNameAsRecordLocalId: 'fileUploaderLocalId', refName: 'fileInput' });
        this._fileUploadId = _.uniqueId('o_FileUploader_fileupload');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get fileUploader() {
        return this.messaging.models['FileUploader'].get(this.props.fileUploaderLocalId);
    }

}

Object.assign(FileUploader, {
    props: {
        fileUploaderLocalId: {
            type: String,
        },
        onAttachmentCreated: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.FileUploader',
});

registerMessagingComponent(FileUploader);
