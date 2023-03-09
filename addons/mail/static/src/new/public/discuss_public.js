/* @odoo-module */

import { Component, useEffect, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
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
        /** @type {import('@mail/new/core/thread_service').ThreadService} */
        this.threadService = useService("mail.thread");
        this.rtc = useService("mail.rtc");
        this.store = useStore();
        this.state = useState({
            welcome: this.props.data.discussPublicViewData.shouldDisplayWelcomeViewInitially,
        });
        useEffect(
            (welcome) => {
                if (!welcome) {
                    this.threadService.setDiscussThread(this.thread, false);
                    this.threadService.fetchChannelMembers(this.thread);
                    const video = browser.localStorage.getItem("mail_call_preview_join_video");
                    const mute = browser.localStorage.getItem("mail_call_preview_join_mute");
                    if (this.thread.defaultDisplayMode === "video_full_screen") {
                        this.rtc.toggleCall(this.thread, { video }).then(() => {
                            if (mute) {
                                this.rtc.toggleMicrophone();
                            }
                        });
                    }
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

    get thread() {
        return this.threadService.insert({
            id: this.props.data.channelData.id,
            model: "mail.channel",
            type: this.props.data.channelData.channel.channel_type,
            serverData: { uuid: this.props.data.channelData.uuid },
        });
    }
}
