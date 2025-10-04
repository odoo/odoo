/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { WelcomePage } from "@mail/discuss/core/public/welcome_page";

import { Component, useEffect, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class DiscussPublic extends Component {
    static components = { Discuss, WelcomePage };
    static props = ["data"];
    static template = "mail.DiscussPublic";

    setup() {
        this.threadService = useService("mail.thread");
        this.store = useState(useService("mail.store"));
        this.state = useState({
            welcome: this.props.data.discussPublicViewData.shouldDisplayWelcomeViewInitially,
        });
        useEffect(
            (welcome) => {
                if (!welcome) {
                    this.displayChannel();
                }
            },
            () => [this.state.welcome]
        );
        if (this.props.data.discussPublicViewData.isChannelTokenSecret) {
            // Change the URL to avoid leaking the invitation link.
            window.history.replaceState(
                window.history.state,
                null,
                `/discuss/channel/${this.thread.id}${window.location.search}`
            );
        }
    }

    displayChannel() {
        this.threadService.setDiscussThread(this.thread, false);
        this.threadService.fetchChannelMembers(this.thread);
    }

    get thread() {
        return this.store.Thread.insert({
            id: this.props.data.channelData.id,
            model: "discuss.channel",
            type: this.props.data.channelData.channel_type,
            uuid: this.props.data.channelData.uuid,
        });
    }
}
