/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/messaging_menu/messaging_menu';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class MessagingMenuContainer extends Component {

    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
    }

    get messaging() {
        return this.env.services.messaging.modelManager.messaging;
    }
}

Object.assign(MessagingMenuContainer, {
    components: { MessagingMenu: getMessagingComponent('MessagingMenu') },
    template: 'mail.MessagingMenuContainer',
});
