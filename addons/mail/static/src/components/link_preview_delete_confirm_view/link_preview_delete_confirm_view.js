/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class LinkPreviewDeleteConfirmView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {DeleteMessageConfirmView}
     */
    get linkPreviewDeleteConfirmView() {
        return this.props.record;
    }

}

Object.assign(LinkPreviewDeleteConfirmView, {
    props: { record: Object },
    template: 'mail.LinkPreviewDeleteConfirmView',
});

registerMessagingComponent(LinkPreviewDeleteConfirmView);
