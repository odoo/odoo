/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class SnailmailError extends Component {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component', modelName: 'SnailmailErrorView' });
    }

    /**
     * @returns {SnailmailErrorView}
     */
    get snailmailErrorView() {
        return this.messaging && this.messaging.models['SnailmailErrorView'].get(this.props.localId);
    }

}

Object.assign(SnailmailError, {
    props: { localId: String },
    template: 'snailmail.SnailmailError',
});

registerMessagingComponent(SnailmailError);
