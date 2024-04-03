/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentDeleteConfirm extends Component {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {AttachmentDeleteConfirmView}
     */
    get attachmentDeleteConfirmView() {
        return this.props.record;
    }

}

Object.assign(AttachmentDeleteConfirm, {
    props: { record: Object },
    template: 'mail.AttachmentDeleteConfirm',
});

registerMessagingComponent(AttachmentDeleteConfirm);
