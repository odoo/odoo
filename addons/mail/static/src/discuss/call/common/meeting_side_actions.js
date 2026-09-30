import { ActionList } from "@mail/core/common/action_list";

import { Component, useSubEnv } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/** @typedef {"chat"|"invite"} MeetingPanel */

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_actions").UseThreadActions} threadActions
 * @extends {Component<Props, Env>}
 */
export class MeetingSideActions extends Component {
    static template = "mail.MeetingSideActions";
    static props = ["threadActions"];
    static components = { ActionList };

    setup() {
        this.store = useService("mail.store");
        useSubEnv({ inMeetingSideActions: true });
    }

    computeActions() {
        const quickThreadActionIds = ["invite-people", "meeting-chat"];
        const threadActions = this.props.threadActions;
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
            threadActions.more({
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
