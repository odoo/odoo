import { useChildSubEnv, useSubEnv } from "@web/owl2/utils";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { Call } from "@mail/discuss/call/common/call";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { useMessageScrolling } from "@mail/utils/common/hooks";

import { Component, onMounted, onWillUnmount, props, signal, types } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { MeetingReadyBanner } from "./meeting_ready_banner";
import { MeetingSideActions } from "./meeting_side_actions";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { useMessageSearch } from "@mail/core/common/message_search_hook";
import { useDynamicInterval } from "@mail/utils/common/misc";

const { DateTime } = luxon;
const PIP_EXTRA_ACTION_IDS = ["copy-invite-link", "meeting-chat"];

/** @typedef {"chat"|"invite"} MeetingPanel */

export class Meeting extends Component {
    static template = "mail.Meeting";
    static components = {
        Call,
        CallActionList,
        Composer,
        Dropdown,
        MeetingReadyBanner,
        MeetingSideActions,
        Thread,
    };

    setup() {
        this.props = props({
            autoOpenAction: types.string().optional(),
            isPip: types.boolean().optional(),
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        this.datetimeNow = signal(DateTime.now());
        useDynamicInterval(() => {
            this.datetimeNow.set(DateTime.now());
            return 60_000 - (Date.now() % 60_000);
        });
        useSubEnv({ inDiscussCallView: true });
        useSubEnv({
            inMeetingView: {
                openChat: () =>
                    this.threadActions.actions
                        .find((action) => action.id === "meeting-chat")
                        ?.actionPanelOpen(),
            },
        });
        this.threadActions = useThreadActions({ thread: () => this.channel.thread });
        this.messageHighlight = useMessageScrolling({ thread: () => this.channel.thread });
        this.messageSearch = useMessageSearch(this.channel.thread);
        useChildSubEnv({
            hasPreviousActionPanel: () => this.threadActions.actionStack.length > 0,
            messageHighlight: this.messageHighlight,
            messageSearch: this.messageSearch,
        });
        onMounted(() => (this.store.meetingViewOpened = true));
        onWillUnmount(() => (this.store.meetingViewOpened = false));
        useHotkey("escape", () => this.onEscape());
    }

    get channel() {
        return this.store.rtc.channel;
    }

    get dateSimple() {
        return this.datetimeNow().toLocaleString(DateTime.TIME_SIMPLE, { locale: user.lang });
    }

    get datetimeMedium() {
        return this.datetimeNow().toLocaleString(DateTime.DATETIME_MED, { locale: user.lang });
    }

    get pipExtraActions() {
        if (!this.rtc.isPipMode) {
            return [];
        }
        return this.threadActions.actions.filter((a) => PIP_EXTRA_ACTION_IDS.includes(a.id));
    }

    onEscape() {
        if (this.threadActions.activeAction) {
            this.threadActions.activeAction.actionPanelClose();
            return true;
        }
        if (this.rtc.isFullscreen) {
            this.rtc.minimize();
            return true;
        }
        return false;
    }
}
