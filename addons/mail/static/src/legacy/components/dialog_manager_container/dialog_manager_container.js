/** @odoo-module **/

import { useMessagingContainer } from "@mail/legacy/component_hooks/use_messaging_container";

import { Component } from "@odoo/owl";

export class DialogManagerContainer extends Component {
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
DialogManagerContainer.props = {};

Object.assign(DialogManagerContainer, {
    template: "mail.DialogManagerContainer",
});
