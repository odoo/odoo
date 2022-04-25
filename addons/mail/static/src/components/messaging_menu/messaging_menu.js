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
        useComponentToModel({ fieldName: 'component', modelName: 'MessagingMenu' });
        /**
         * global JS generated ID for this component. Useful to provide a
         * custom class to autocomplete input, so that click in an autocomplete
         * item is not considered as a click away from messaging menu in mobile.
         */
        this.id = _.uniqueId('o_messagingMenu_');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MessagingMenu}
     */
    get messagingMenu() {
        return this.messaging && this.messaging.models['MessagingMenu'].get(this.props.localId);
    }

}

Object.assign(MessagingMenu, {
    props: { localId: String },
    template: 'mail.MessagingMenu',
});

registerMessagingComponent(MessagingMenu);
