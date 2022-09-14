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

    get global() {
        return this.env.services.messaging.modelManager.global;
    }
}

Object.assign(MessagingMenuContainer, {
    components: { MessagingMenu: getMessagingComponent('MessagingMenu') },
    template: 'mail.MessagingMenuContainer',
});
