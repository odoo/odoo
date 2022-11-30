/** @odoo-module */

import { reactive } from "@odoo/owl";

export const activityService = {
    dependencies: ["orm", "action", "bus_service", "mail.messaging"],
    async: ["scheduleActivity", "markAsDoneAndScheduleNext"],
    start(env, { orm, action, bus_service: bus, "mail.messaging": messaging }) {
        const state = reactive({
            counter: 0,
            feedback: {},
            activities: [],
        });

        // not waiting for this on purpose: we do not want to delay the web client
        orm.call("res.users", "systray_get_activities").then((activities) => {
            let total = 0;
            for (const activity of activities) {
                total += activity.total_count;
            }
            state.counter = total;
            state.activities = activities;
        });

        async function scheduleActivity(
            resModel,
            resId,
            activityId = false,
            defaultActivityTypeId = undefined
        ) {
            const context = {
                default_res_model: resModel,
                default_res_id: resId,
            };
            if (defaultActivityTypeId !== undefined) {
                context.default_activity_type_id = defaultActivityTypeId;
            }
            return new Promise((resolve) => {
                action.doAction(
                    {
                        type: "ir.actions.act_window",
                        name: env._t("Schedule Activity"),
                        res_model: "mail.activity",
                        view_mode: "form",
                        views: [[false, "form"]],
                        target: "new",
                        context,
                        res_id: activityId,
                    },
                    { onClose: resolve }
                );
            });
        }

        async function markAsDone(id) {
            await orm.call("mail.activity", "action_feedback", [[id]], {
                feedback: state.feedback[id],
            });
        }

        async function markAsDoneAndScheduleNext(activity, thread) {
            await markAsDone(activity.id);
            await messaging.fetchThreadMessagesNew(thread.id);
            await scheduleActivity(thread.resModel, thread.resId);
        }

        bus.addEventListener("notification", (notifEvent) => {
            for (const notif of notifEvent.detail) {
                if (notif.type === "mail.activity/updated") {
                    if (notif.payload.activity_created) {
                        state.counter++;
                    }
                    if (notif.payload.activity_deleted) {
                        state.counter--;
                    }
                }
            }
        });

        return {
            state,
            scheduleActivity,
            markAsDone,
            markAsDoneAndScheduleNext,
        };
    },
};
