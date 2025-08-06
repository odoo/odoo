import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { Component, onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Call } from "./call";
import { CallActionList } from "./call_action_list";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";

/** @typedef {"chat"|"invite"} MeetingPanel */

/**
 * @typedef {Object} Props
 * @property {"invite"|"chat"} initialSidePanel
 * @extends {Component<Props, Env>}
 */
export class Meeting extends Component {
    static template = "mail.Meeting";
    static props = ["initialSidePanel?"];
    static components = { Call, CallActionList, Composer, Thread, ChannelInvitation };

    setup() {
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.state = useState({
            isSidePanelOpened: Boolean(this.props.initialSidePanel),
            activeSidePanel: this.props.initialSidePanel,
            jumpPresent: 0,
        });
        useEffect(
            (chatOpened) => {
                if (!this.state.chatAlreadyOpened && chatOpened) {
                    this.state.chatAlreadyOpened = true;
                }
            },
            () => [this.store.rtc.meetingChatOpened]
        );
        onMounted(() => (this.store.rtc.inMeeting = true));
        onWillUnmount(() => {
            this.store.rtc.inMeeting = false;
            this.store.rtc.meetingChatOpened = false;
        });
    }

    get channel() {
        return this.store.rtc.channel;
    }

    /** @param {MeetingPanel} panelName */
    toggleSidePanel(panelName) {
        if (!this.state.isSidePanelOpened) {
            this.state.activeSidePanel = panelName;
            this.state.isSidePanelOpened = true;
        } else if (this.state.activeSidePanel === panelName) {
            this.state.isSidePanelOpened = false;
        } else {
            this.state.activeSidePanel = panelName;
        }
    }

    get toggleChatPanelTitle() {
        return this.state.activeSidePanel === "chat" ? _t("Close chat") : _t("Open chat");
    }

    get toggleInvitePanelTitle() {
        return this.state.activeSidePanel === "invite" ? _t("Close invite") : _t("Open invite");
    }

    get channelInvitationState() {
        return {
            searchPlaceholder: "Enter name or email",
        };
    }
}
