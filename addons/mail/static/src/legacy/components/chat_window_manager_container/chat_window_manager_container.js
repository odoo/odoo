/** @odoo-module **/

import { useMessagingContainer } from "@mail/legacy/component_hooks/use_messaging_container";

import { Component } from "@odoo/owl";

export class ChatWindowManagerContainer extends Component {
    /**
     * @override
     */
    setup() {
        useMessagingContainer();
    }

    get messaging() {
        return this.env.services.messaging.modelManager.messaging;
    }
}
ChatWindowManagerContainer.props = {};

Object.assign(ChatWindowManagerContainer, {
    template: "mail.ChatWindowManagerContainer",
});
