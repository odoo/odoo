import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { Call } from "@mail/discuss/call/common/call";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import {
    inDiscussCallViewProps,
    useInDiscussCallView,
    useMessageScrolling,
} from "@mail/utils/common/hooks";

import { Component, onMounted, onWillUnmount, useChildSubEnv, useSubEnv } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";
import { MeetingSideActions } from "./meeting_side_actions";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { useMessageSearch } from "@mail/core/common/message_search_hook";

/** @typedef {"chat"|"invite"} MeetingPanel */

/**
 * @typedef {Object} Props
 * @property {ThreadActionDefinition.id} [autoOpenAction]
 * @extends {Component<Props, Env>}
 */
export class Meeting extends Component {
    static template = "mail.Meeting";
    static props = ["autoOpenAction?", ...inDiscussCallViewProps];
    static components = {
        Call,
        CallActionList,
        ChannelInvitation,
        Composer,
        Dropdown,
        MeetingSideActions,
        Thread,
    };

    setup() {
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        onMounted(() => {
            if (this.props.autoOpenAction) {
                this.threadActions.actions
                    .find((a) => a.id === this.props.autoOpenAction)
                    ?.onSelected();
            }
        });
        useInDiscussCallView();
        useSubEnv({
            inMeetingView: {
                openChat: () =>
                    this.threadActions.actions
                        .find((action) => action.id === "meeting-chat")
                        ?.open(),
            },
        });
        this.threadActions = useThreadActions({ thread: () => this.thread });
        this.messageHighlight = useMessageScrolling();
        this.messageSearch = useMessageSearch(this.thread);
        useChildSubEnv({
            closeActionPanel: () => this.threadActions.activeAction?.close(),
            messageHighlight: this.messageHighlight,
            messageSearch: this.messageSearch,
        });
        onMounted(() => (this.store.meetingViewOpened = true));
        onWillUnmount(() => (this.store.meetingViewOpened = false));
    }

    get thread() {
        return this.store.rtc.channel;
    }
}
