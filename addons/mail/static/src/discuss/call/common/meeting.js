import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { Call } from "@mail/discuss/call/common/call";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";

import { Component, onMounted, onWillUnmount, providePlugins, types, useProps } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { MeetingReadyBanner } from "./meeting_ready_banner";
import { meetingMoreActionGroups, MeetingSideActions } from "./meeting_side_actions";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { assignGetter } from "@mail/utils/common/misc";

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
        this.props = useProps({
            autoOpenAction: types.string().optional(),
            isPip: types.boolean().optional(),
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        useAncestors({
            inDiscussCallTheme: true,
            inDiscussCallView: true,
            inMeetingView: assignGetter(
                {
                    openChat: () =>
                        this.threadActions.actions
                            .find((action) => action.id === "meeting-chat")
                            ?.actionPanelOpen(),
                },
                { hasPreviousActionPanel: () => this.threadActions.actionStack.length > 0 }
            ),
        });
        this.threadActions = useThreadActions({ thread: () => this.channel.thread });
        providePlugins([MessageHighlightPlugin], { thread: () => this.channel.thread });
        onMounted(() => (this.store.meetingViewOpened = true));
        onWillUnmount(() => (this.store.meetingViewOpened = false));
        useHotkey("escape", () => this.onEscape());
    }

    get channel() {
        return this.store.rtc.channel;
    }

    get dateSimple() {
        return this.store.startOfMinute.toLocaleString(DateTime.TIME_SIMPLE, {
            locale: user.lang,
        });
    }

    get datetimeMedium() {
        return this.store.startOfMinute.toLocaleString(DateTime.DATETIME_MED, {
            locale: user.lang,
        });
    }

    /** @returns {boolean} */
    get showInviteBanner() {
        return Boolean(
            this.channel &&
                !this.rtc.isPipMode &&
                this.channel.channel_type !== "chat" &&
                !this.rtc.isMeetingReadyBannerDismissed &&
                this.channel.rtc_session_ids.length <= 1
        );
    }

    /** Handed to the call bar's "More" when this bar has no room for a cluster of its own. */
    get sideActionGroups() {
        // PiP has its own, much shorter list ({@link pipExtraActions}).
        if (this.hasSideActions || this.rtc.isPipMode) {
            return [];
        }
        return meetingMoreActionGroups(this.threadActions);
    }

    get hasSideActions() {
        return !this.rtc.isPipMode && !this.ui.isSmall;
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
        if (this.rtc.isFullscreen && !this.rtc.isBrowserFullscreen) {
            this.rtc.minimize();
            return true;
        }
        return false;
    }
}
