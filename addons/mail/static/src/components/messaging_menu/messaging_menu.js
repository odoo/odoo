/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessagingMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MessagingMenu}
     */
    get messagingMenu() {
        return this.props.record;
    }

}

Object.assign(MessagingMenu, {
    props: { record: Object },
    template: 'mail.MessagingMenu',
});

registerMessagingComponent(MessagingMenu);
