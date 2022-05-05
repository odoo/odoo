/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/messaging_menu/messaging_menu';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, useSubEnv } = owl;

export class MessagingMenuContainer extends Component {

    /**
     * @override
     */
    setup() {
        // for now, the legacy env is needed for internal functions such as
        // `useModels` to work
        useSubEnv(Component.env);
        useModels();
        super.setup();
    }

}

Object.assign(MessagingMenuContainer, {
    components: { MessagingMenu: getMessagingComponent('MessagingMenu') },
    template: 'mail.MessagingMenuContainer',
});
