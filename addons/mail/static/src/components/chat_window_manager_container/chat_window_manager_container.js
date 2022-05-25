/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/chat_window_manager/chat_window_manager';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, useSubEnv } = owl;

export class ChatWindowManagerContainer extends Component {

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

Object.assign(ChatWindowManagerContainer, {
    components: { ChatWindowManager: getMessagingComponent('ChatWindowManager') },
    template: 'mail.ChatWindowManagerContainer',
});
