/** @odoo-module */

import { registry } from "@web/core/registry";

export const timerHelpdeskService = {
    dependencies: ["orm", "user"],
    async: [
        "fetchHelpdeskProjects",
    ],
    start(env, { orm, user }) {
        let helpdeskProjects;
        return {
            async fetchHelpdeskProjects() {
                const isHelpdeskUser = await user.hasGroup("helpdesk.group_helpdesk_user");
                if (!isHelpdeskUser) {
                    return [];
                }
                const result = await orm.readGroup(
                    "helpdesk.ticket",
                    [["project_id", "!=", false]],
                    ["project_id"],
                    ["project_id"],
                );
                if (result?.length) {
                    helpdeskProjects = result.map((r) => r.project_id[0]);
                }
            },
            get helpdeskProjects() {
                return helpdeskProjects;
            },
            invalidateCache() {
                helpdeskProjects = undefined;
            }
        };
    }
};

registry.category('services').add('helpdesk_timer_header', timerHelpdeskService);
