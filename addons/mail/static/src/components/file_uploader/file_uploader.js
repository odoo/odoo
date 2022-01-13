/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FileUploader extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'fileInputRef', modelName: 'FileUploaderView', refName: 'fileInput' });
    }

    get fileUploaderView() {
        return this.messaging && this.messaging.models['FileUploaderView'].get(this.props.localId);
    }

}

Object.assign(FileUploader, {
    props: { localId: String },
    template: 'mail.FileUploader',
});

registerMessagingComponent(FileUploader);
