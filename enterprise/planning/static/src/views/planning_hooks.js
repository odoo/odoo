/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { markup, useEnv, onWillUnmount, useEffect } from "@odoo/owl";
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
                        "Previous week's shifts copied"
                    ))}</span>`
                ),
                {
                    type: "success",
                    sticky: true,
                    className: "planning_notification",
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
                                        "Previous week's copied shifts removed"
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
        const res = await this.orm.call(this.getResModel(), "auto_plan_ids", [this.autoPlanDomain()], {
            context: additionalContext,
        });
        const { open_shift_assigned = [], sale_line_planned = [] } = res;
        if (!open_shift_assigned.length && !sale_line_planned.length) {
            this.notifications.add(this.autoPlanFailureNotification(), { type: "danger" });
            return;
        }
        let multipleClickProtection = false;
        const notificationRemove = this.notifications.add(
            markup(
                `<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(
                    this.autoPlanSuccessNotification()
                )}</span>`
            ),
            {
                type: "success",
                sticky: true,
                buttons: [
                    {
                        name: "Undo",
                        icon: "fa-undo",
                        onClick: async () => {
                            if (multipleClickProtection) {
                                return;
                            }
                            multipleClickProtection = true;
                            await this.orm.call(
                                this.getResModel(),
                                "action_rollback_auto_plan_ids",
                                [res]
                            );
                            await this.reload();
                            this.notifications.add(
                                markup(
                                    `<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(
                                        this.autoPlanRollbackSuccessNotification()
                                    )}</span>`
                                ),
                                { type: "success" }
                            );
                            this.toggleHighlightPlannedFilter(false);
                            notificationRemove();
                        },
                    },
                ],
            }
        );
        this.toggleHighlightPlannedFilter([...open_shift_assigned, ...sale_line_planned]);
        this.notificationFn = notificationRemove;
    }

    autoPlanDomain() {
        return this.getDomain();
    }

    autoPlanSuccessNotification() {
        return _t("Open shifts assigned");
    }

    autoPlanFailureNotification() {
        return _t(
            "All open shifts have already been assigned, or there are no resources available to take them at this time."
        );
    }

    autoPlanRollbackSuccessNotification() {
        return _t("Open shifts unscheduled");
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

export function setupDisplayName(displayNameRef) {
    useEffect(
        (displayNameEl) => {
            const displayNameMatch = displayNameEl.textContent.match(/^(.*)(\(.*\))$/);
            if (displayNameMatch) {
                const textMuted = document.createElement("span");
                textMuted.className = "text-muted text-truncate";
                textMuted.textContent = displayNameMatch[2];
                const displayNameText = document.createElement("span");
                displayNameText.textContent = displayNameMatch[1];
                displayNameEl.replaceChildren(displayNameText);
                displayNameEl.appendChild(textMuted);
            } else {
                displayNameEl.replaceChildren(document.createTextNode(displayNameEl.textContent));
            }
        },
        () => [displayNameRef.el]
    );
}

export function usePlanningRecurringDeleteAction() {
    const orm = useService("orm");
    return {
        async _actionAddressRecurrency(shift, recurrenceUpdate) {
            if (['subsequent', 'all'].includes(recurrenceUpdate)) {
                await orm.call(
                    shift.resModel,
                    'action_address_recurrency',
                    [shift.resId, recurrenceUpdate],
                );
            }
        },
        _setRecurrenceUpdate(recurrenceUpdate) {
            this.state.recurrenceUpdate = recurrenceUpdate;
        },
    };
}
