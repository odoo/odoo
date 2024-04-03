/** @odoo-module **/

import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DialogManager extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    get dialogManager() {
        return this.props.record;
    }
}

Object.assign(DialogManager, {
    props: { record: Object },
    template: 'mail.DialogManager',
});

registerMessagingComponent(DialogManager);
