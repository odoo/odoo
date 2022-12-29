/* @odoo-module */

import { Component, useEffect, useState } from "@odoo/owl";
import { WelcomePage } from "./welcome_page";
import { Discuss } from "./../discuss/discuss";
import { useMessaging, useStore } from "../core/messaging_hook";
import { useService } from "@web/core/utils/hooks";

export class DiscussPublic extends Component {
    static components = { Discuss, WelcomePage };
    static props = ["data"];
    static template = "mail.discuss_public";

    setup() {
        this.messaging = useMessaging();
        this.threadService = useService("mail.thread");
        this.store = useStore();
        this.state = useState({
            welcome: this.props.data.discussPublicViewData.shouldDisplayWelcomeViewInitially,
        });
        useEffect(
            (welcome) => {
                if (!welcome) {
                    this.threadService.fetchChannelMembers(this.thread);
                    // Change the URL to avoid leaking the invitation link.
                    window.history.replaceState(
                        window.history.state,
                        null,
                        `/discuss/channel/${this.thread.id}${window.location.search}`
                    );
                }
            },
            () => [this.state.welcome]
        );
        this.threadService = useService("mail.thread");
        this.threadService.setDiscussThread(this.thread);
    }

    get thread() {
        return this.threadService.insert({
            id: this.props.data.channelData.id,
            model: "mail.channel",
            type: this.props.data.channelData.channel.channel_type,
            serverData: { uuid: this.props.data.channelData.uuid },
        });
    }
}
