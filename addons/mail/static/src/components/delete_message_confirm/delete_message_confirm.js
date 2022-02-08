/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DeleteMessageConfirm extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'DeleteMessageConfirmView' });
    }

    /**
     * @returns {DeleteMessageConfirmView}
     */
    get deleteMessageConfirmView() {
        return this.messaging && this.messaging.models['DeleteMessageConfirmView'].get(this.props.localId);
    }

}

Object.assign(DeleteMessageConfirm, {
    props: { localId: String },
    template: 'mail.DeleteMessageConfirm',
});

registerMessagingComponent(DeleteMessageConfirm);
