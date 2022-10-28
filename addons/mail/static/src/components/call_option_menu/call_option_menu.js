/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallOptionMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {CallOptionMenu}
     */
    get callOptionMenu() {
        return this.props.record;
    }

}

Object.assign(CallOptionMenu, {
    props: { record: Object },
    template: 'mail.CallOptionMenu',
});

registerMessagingComponent(CallOptionMenu);
