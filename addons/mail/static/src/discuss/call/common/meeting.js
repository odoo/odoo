import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { Call } from "@mail/discuss/call/common/call";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";

import { Component, onMounted, onWillUnmount, useChildSubEnv, useRef, useState } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/** @typedef {"chat"|"invite"} MeetingPanel */

/**
 * @typedef {Object} Props
 * @property {MeetingPanel} initialSidePanel
 * @extends {Component<Props, Env>}
 */
export class Meeting extends Component {
    static template = "mail.Meeting";
    static props = ["initialSidePanel?"];
    static components = { Call, CallActionList, ChannelInvitation, Composer, Thread };

    setup() {
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        this.state = useState({
            activeSidePanel: this.props.initialSidePanel,
            jumpPresent: 0,
        });
        this.sidePanelRef = useRef("sidePanel");
        this.isMobileOS = isMobileOS();
        onMounted(() => (this.store.meetingViewOpened = true));
        onWillUnmount(() => (this.store.meetingViewOpened = false));
        useChildSubEnv({ inMeetingView: true });
    }

    /** @param {MeetingPanel} panelName */
    toggleSidePanel(panelName) {
        this.state.activeSidePanel = this.state.activeSidePanel === panelName ? null : panelName;
    }

    get toggleChatPanelTitle() {
        return this.state.activeSidePanel === "chat" ? _t("Close chat") : _t("Chat");
    }

    get toggleInvitePanelTitle() {
        return this.state.activeSidePanel === "invite" ? _t("Close invite") : _t("Invite people");
    }

    get channelInvitationState() {
        return { searchPlaceholder: _t("Enter name or email") };
    }
}
