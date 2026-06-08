import { ActionList } from "@mail/core/common/action_list";
import { UseThreadActions } from "@mail/core/common/thread_actions";

import { Component, props, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { useSubEnv } from "@web/owl2/utils";

/** @typedef {"chat"|"invite"} MeetingPanel */

export class MeetingSideActions extends Component {
    static template = "mail.MeetingSideActions";
    static components = { ActionList };

    setup() {
        this.store = useService("mail.store");
        this.props = props({
            threadActions: types.instanceOf(UseThreadActions),
        });
        this.ui = useService("ui");
        useSubEnv({ inMeetingSideActions: true });
    }

    get callActionsParams() {
        return { channel: () => this.store.rtc.channel };
    }

    computeActions() {
        const threadActions = this.props.threadActions;
        if (this.store.rtc.channel.default_display_mode === "video_full_screen") {
            this.actions = threadActions.actions.filter((action) =>
                ["member-list", "meeting-chat"].includes(action.id)
            );
            return;
        }
        const quickThreadActionIds = this.ui.isSmall ? [] : ["invite-people", "meeting-chat"];
        const { quick, other, group } = threadActions.partition;
        const partitionedActions = {
            quick: quick.filter((action) => !quickThreadActionIds.includes(action.id)),
            other: other.filter((action) => !quickThreadActionIds.includes(action.id)),
            group: group
                .map((group) => group.filter((action) => !quickThreadActionIds.includes(action.id)))
                .filter((g) => g.length > 0),
        };
        const actions = threadActions.actions.filter((action) =>
            quickThreadActionIds.includes(action.id)
        );
        actions.push(
            threadActions.more(this.callActionsParams, {
                actions: [
                    partitionedActions.quick,
                    partitionedActions.other,
                    ...partitionedActions.group,
                ],
            })
        );
        this.actions = actions;
    }
}
