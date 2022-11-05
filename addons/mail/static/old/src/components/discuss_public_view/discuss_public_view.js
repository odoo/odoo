/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";

import { Component } from "@odoo/owl";

class DiscussPublicView extends Component {
    /**
     * @returns {DiscussPublicView}
     */
    get discussPublicView() {
        return this.props.record;
    }
}

Object.assign(DiscussPublicView, {
    props: { record: Object },
    template: "mail.DiscussPublicView",
});

registerMessagingComponent(DiscussPublicView);
