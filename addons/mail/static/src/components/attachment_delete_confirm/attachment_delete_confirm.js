/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class AttachmentDeleteConfirm extends Component {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component', modelName: 'AttachmentDeleteConfirmView' });
    }

    /**
     * @returns {AttachmentDeleteConfirmView}
     */
    get attachmentDeleteConfirmView() {
        return this.messaging && this.messaging.models['AttachmentDeleteConfirmView'].get(this.props.localId);
    }

}

Object.assign(AttachmentDeleteConfirm, {
    props: { localId: String },
    template: 'mail.AttachmentDeleteConfirm',
});

registerMessagingComponent(AttachmentDeleteConfirm);
