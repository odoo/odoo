/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/chat_window_manager/chat_window_manager';
import { getMessagingComponent } from "@mail/utils/messaging_component";

import { Component } from '@odoo/owl';

export class ChatWindowManagerContainer extends Component {

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
ChatWindowManagerContainer.props = {};

Object.assign(ChatWindowManagerContainer, {
    components: { ChatWindowManager: getMessagingComponent('ChatWindowManager') },
    template: 'mail.ChatWindowManagerContainer',
});
