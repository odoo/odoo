/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class AttachmentDeleteConfirmView extends Component {

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

Object.assign(AttachmentDeleteConfirmView, {
    props: { record: Object },
    template: 'mail.AttachmentDeleteConfirmView',
});

registerMessagingComponent(AttachmentDeleteConfirmView);
