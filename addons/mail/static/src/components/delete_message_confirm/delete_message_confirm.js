/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DeleteMessageConfirm extends Component {

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
    get deleteMessageConfirmView() {
        return this.props.record;
    }

}

Object.assign(DeleteMessageConfirm, {
    props: { record: Object },
    template: 'mail.DeleteMessageConfirm',
});

registerMessagingComponent(DeleteMessageConfirm);
