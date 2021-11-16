/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;
const { useRef } = owl.hooks;

export class FileUploader extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._fileInputRef = useRef('fileInput');
        this._fileUploadId = _.uniqueId('o_FileUploader_fileupload');

        useComponentToModel({ fieldName: 'component', modelName: 'mail.file_uploader_view', propNameAsRecordLocalId: 'fileUploaderViewLocalId' });
        useRefToModel({ fieldName: 'fileUploaderRef', modelName: 'mail.file_uploader_view', propNameAsRecordLocalId: 'fileUploaderViewLocalId', refName: 'fileInput' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    openBrowserFileUploader() {
        this._fileInputRef.el.click();
    }

    get fileUploaderView() {
        return this.messaging.models['mail.file_uploader_view'].get(this.props.fileUploaderViewLocalId);
    }

}

Object.assign(FileUploader, {
    props: {
        composerViewLocalId: {
            type: String,
            optional: true,
        },
        fileUploaderViewLocalId: {
            type: String,
            optional: true,
        },
    },
    template: 'mail.FileUploader',
});

registerMessagingComponent(FileUploader);
