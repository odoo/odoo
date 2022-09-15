/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallOptionMenuView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {CallOptionMenuView}
     */
    get callOptionMenuView() {
        return this.props.record;
    }

}

Object.assign(CallOptionMenuView, {
    props: { record: Object },
    template: 'mail.CallOptionMenuView',
});

registerMessagingComponent(CallOptionMenuView);
