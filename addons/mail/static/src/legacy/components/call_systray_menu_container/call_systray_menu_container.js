/** @odoo-module **/

import { useMessagingContainer } from "@mail/legacy/component_hooks/use_messaging_container";

import { Component } from "@odoo/owl";

export class CallSystrayMenuContainer extends Component {
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
CallSystrayMenuContainer.props = {};

Object.assign(CallSystrayMenuContainer, {
    template: "mail.CallSystrayMenuContainer",
});
