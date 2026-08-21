import { ActionList } from "@mail/core/common/action_list";
import { UseThreadActions } from "@mail/core/common/thread_actions";
import { attClassObjectToString } from "@mail/utils/common/format";

import { Component, computed, types, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/** @typedef {"chat"|"invite"} MeetingPanel */

/** Thread actions a meeting has no use for, wherever its actions end up being rendered. */
const HIDDEN_ACTION_IDS = ["advanced-settings", "leave"];
/** Thread actions a bar with room to spare shows as their own button. */
const QUICK_ACTION_IDS = ["member-list", "meeting-chat"];

/**
 * The thread actions of a meeting, grouped for a "More" menu: everything the thread offers except
 * what is already a button of its own and what a meeting hides outright.
 *
 * Exported because a small screen does not render the side actions at all — their menu goes into
 * the call bar's own "More", so that a phone has one menu instead of two side by side.
 *
 * @param {import("@mail/core/common/thread_actions").UseThreadActions} threadActions
 * @param {string[]} [shownActionIds] ids already rendered as their own button
 * @returns {Array<Array>} non-empty action groups
 */
export function meetingMoreActionGroups(threadActions, shownActionIds = []) {
    const inMore = (action) =>
        !shownActionIds.includes(action.id) && !HIDDEN_ACTION_IDS.includes(action.id);
    const { quick, other, group } = threadActions.partition;
    return [
        quick.filter(inMore),
        other.filter(inMore),
        ...group.map((actions) => actions.filter(inMore)),
    ].filter((actions) => actions.length);
}

export class MeetingSideActions extends Component {
    static template = "mail.MeetingSideActions";
    static components = { ActionList };

    setup() {
        this.store = useService("mail.store");
        this.props = useProps({
            threadActions: types.instanceOf(UseThreadActions),
        });
    }

    get callActionsParams() {
        return { channel: () => this.store.rtc.channel };
    }

    actions = computed(() => {
        const threadActions = this.props.threadActions;
        // the channel can already be gone while the meeting view tears down
        if (this.store.rtc.channel?.default_display_mode === "video_full_screen") {
            return threadActions.actions.filter((action) => QUICK_ACTION_IDS.includes(action.id));
        }
        const actions = threadActions.actions.filter((action) =>
            QUICK_ACTION_IDS.includes(action.id)
        );
        actions.push(
            threadActions.more(this.callActionsParams, {
                actions: meetingMoreActionGroups(threadActions, QUICK_ACTION_IDS),
                dropdownMenuClass: attClassObjectToString({
                    "o-discuss-CallActionList-menu": Boolean(this.env.inMeetingView),
                }),
            })
        );
        return actions;
    });
}
