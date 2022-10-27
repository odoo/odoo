/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class SnailmailErrorView extends Component {

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

Object.assign(SnailmailErrorView, {
    props: { record: Object },
    template: 'snailmail.SnailmailErrorView',
});

registerMessagingComponent(SnailmailErrorView);
