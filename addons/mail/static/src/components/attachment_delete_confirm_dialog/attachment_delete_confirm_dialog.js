/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

import Dialog from 'web.OwlDialog';

const { Component } = owl;

export class AttachmentDeleteConfirmDialog extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'dialogRef', modelName: 'AttachmentDeleteConfirmDialogView', refName: 'root' });
    }

    /**
     * @returns {AttachmentDeleteConfirmDialogView}
     */
    get attachmentDeleteConfirmDialogView() {
        return this.messaging && this.messaging.models['AttachmentDeleteConfirmDialogView'].get(this.props.localId);
    }

}

Object.assign(AttachmentDeleteConfirmDialog, {
    components: { Dialog },
    props: {
        localId: String,
        onClosed: {
            type: Function,
            optional: true,
        }
    },
    template: 'mail.AttachmentDeleteConfirmDialog',
});

registerMessagingComponent(AttachmentDeleteConfirmDialog);
