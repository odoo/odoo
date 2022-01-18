/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

class SnailmailError extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
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

export default SnailmailError;
