/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageContextMenu extends Component {

    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }
    
    /**
     * @returns {MessageContextMenu}
     */
    get messageContextMenu() {
        return this.props.record;
    }

}

Object.assign(MessageContextMenu, {
    props: { record: Object },
    template: 'mail.MessageContextMenu',
});

registerMessagingComponent(MessageContextMenu);
