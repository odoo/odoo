/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class SnailmailError extends Component {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {SnailmailErrorView}
     */
    get snailmailErrorView() {
        return this.props.record;
    }

}

Object.assign(SnailmailError, {
    props: { record: Object },
    template: 'snailmail.SnailmailError',
});

registerMessagingComponent(SnailmailError);
