/** @odoo-module **/

import { useMessagingContainer } from "@mail/component_hooks/use_messaging_container";

import { Component } from "@odoo/owl";

export class DiscussPublicViewContainer extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useMessagingContainer();
        this.env.services.messaging.get().then((messaging) => {
            messaging.models["Thread"].insert(
                messaging.models["Thread"].convertData(this.props.data.channelData)
            );
            this.discussPublicView = messaging.models["DiscussPublicView"].insert(
                this.props.data.discussPublicViewData
            );
            if (this.discussPublicView.shouldDisplayWelcomeViewInitially) {
                this.discussPublicView.switchToWelcomeView();
            } else {
                this.discussPublicView.switchToThreadView();
            }
            this.render();
        });
    }
}

Object.assign(DiscussPublicViewContainer, {
    template: "mail.DiscussPublicViewContainer",
    props: {
        data: Object,
    },
});
