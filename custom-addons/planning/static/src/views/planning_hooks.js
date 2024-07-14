/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { markup, useEnv, onWillUnmount } from "@odoo/owl";
import { serializeDateTime } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

/**
 * @param {Object} params
 * @param {() => any} params.getAdditionalContext
 * @param {() => any} params.getDomain
 * @param {() => any} params.getRecords
 * @param {() => any} params.getResModel
 * @param {() => luxon.DateTime} params.getStartDate
 * @param {() => any} params.toggleHighlightPlannedFilter
 * @param {() => Promise<any>} params.reload
 */
export class PlanningControllerActions {
    constructor({
        getAdditionalContext,
        getDomain,
        getRecords,
        getResModel,
        getStartDate,
        toggleHighlightPlannedFilter,
        reload,
    }) {
        this.getAdditionalContext = getAdditionalContext;
        this.getDomain = getDomain;
        this.getRecords = getRecords;
        this.getResModel = getResModel;
        this.getStartDate = getStartDate;
        this.toggleHighlightPlannedFilter = toggleHighlightPlannedFilter;
        this.reload = reload;
        this.actionService = useService("action");
        this.env = useEnv();
        this.notifications = useService("notification");
        this.orm = useService("orm");
    }

    async copyPrevious() {
        const resModel = this.getResModel();
        const startDate = serializeDateTime(this.getStartDate());
        const domain = this.getDomain();
        const result = await this.orm.call(resModel, "action_copy_previous_week", [
            startDate,
            domain,
        ]);
        if (result) {
            const notificationRemove = this.notifications.add(
                markup(
                    `<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(_t(
                        "The shifts from the previous week have successfully been copied."
                    ))}</span>`
                ),
                {
                    type: "success",
                    sticky: true,
                    buttons: [{
                        name: 'Undo',
                        icon: 'fa-undo',
                        onClick: async () => {
                            await this.orm.call(
                                resModel,
                                'action_rollback_copy_previous_week',
                                result,
                            );
                            this.toggleHighlightPlannedFilter(false);
                            this.notifications.add(
                                markup(
                                    `<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(_t(
                                        "The shifts that had been copied from the previous week have successfully been removed."
                                    ))}</span>`
                                ),
                                { type: 'success' },
                            );
                            notificationRemove();
                        },
                    }],
                }
            );
            this.toggleHighlightPlannedFilter(result[0]);

            this.notificationFn = notificationRemove;

        } else {
            this.notifications.add(
                _t(
                    "There are no shifts planned for the previous week, or they have already been copied."
                ),
                { type: "danger" }
            );
        }
    }

    async publish() {
        const records = this.getRecords();
        if (!records?.length) {
            return this.notifications.add(
                _t(
                    "The shifts have already been published, or there are no shifts to publish."
                ),
                { type: "danger" }
            );
        }
        return this.actionService.doAction("planning.planning_send_action", {
            additionalContext: this.getAdditionalContext(),
            onClose: this.reload,
        });
    }

    async autoPlan() {
        const additionalContext = this.getAdditionalContext();
        const highlightPlannedIds = await this.orm.call(
            this.getResModel(),
            "auto_plan_ids",
            [this.getDomain()],
            {
                context: additionalContext,
            }
        );
        if (!highlightPlannedIds.length) {
            this.notifications.add(
                this.autoPlanFailureNotification(),
                { type: "danger" }
            );
        } else {
            this.notifications.add(
                this.autoPlanSuccessNotification(),
                { type: "success" }
            );
            if (this.env.searchModel.highlightPlannedIds) {
                this.toggleHighlightPlannedFilter(this.env.searchModel.highlightPlannedIds);
            }
            this.toggleHighlightPlannedFilter(highlightPlannedIds);
        }
    }

    autoPlanSuccessNotification() {
        return _t("The open shifts have been successfully assigned.");
    }

    autoPlanFailureNotification() {
        return _t(
            "All open shifts have already been assigned, or there are no resources available to take them at this time."
        );
    }
}

export function usePlanningControllerActions() {
    const planningControllerActions = new PlanningControllerActions(...arguments);

    onWillUnmount(() => {
        planningControllerActions.notificationFn?.();
    });

    return planningControllerActions;
}

export function usePlanningModelActions({
    getHighlightPlannedIds,
    getContext,
}) {
    const orm = useService("orm");
    return {
        async getHighlightIds() {
            const context = getContext();
            if (!context.highlight_conflicting && !context.highlight_planned) {
                return;
            }

            if (context.highlight_conflicting) {
                const highlightConflictingIds = await orm.search(
                    "planning.slot",
                    [["overlap_slot_count", ">", 0]],
                );

                if (context.highlight_planned) {
                    return Array.from(
                        new Set([...highlightConflictingIds, ...getHighlightPlannedIds()])
                    );
                }
                return highlightConflictingIds;
            }
            return getHighlightPlannedIds() || [];
        },
    };
}
