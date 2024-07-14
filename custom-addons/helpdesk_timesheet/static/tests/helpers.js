/** @odoo-module */

import { patch } from "@web/core/utils/patch";

import { registry } from "@web/core/registry";
import { timerHelpdeskService } from "@helpdesk_timesheet/services/helpdesk_timer_header_service";
import { TimesheetGridSetupHelper, timesheetListSetupHelper } from "@timesheet_grid/../tests/helpers";

const serviceRegistry = registry.category("services");

patch(timesheetListSetupHelper, {
    setupTimesheetList() {
        super.setupTimesheetList();
        serviceRegistry.add("helpdesk_timer_header", timerHelpdeskService, { force: true });
    },
});

patch(TimesheetGridSetupHelper.prototype, {
    async mockTimesheetGridRPC(route, args) {
        const result = await super.mockTimesheetGridRPC(route, args);
        if (route === '/web/dataset/call_kw/res.users/has_group') {
            return true;
        }
        return result;
    },
    async setupTimesheetGrid() {
        serviceRegistry.add("helpdesk_timer_header", timerHelpdeskService, { force: true });
        const result = await super.setupTimesheetGrid();
        if (this.withTimer) {
            const { pyEnv } = result;
            const projectId5 = pyEnv.mockServer.pyEnv['project.project'].create({ display_name: "helpdesk Project" });
            pyEnv.mockServer.models["helpdesk.team"] = {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Description", type: "char" },
                    project_id: {
                        string: "Project",
                        type: "many2one",
                        relation: "project.project",
                    },
                },
                records: [
                    {
                        id: 1,
                        project_id: projectId5,
                        name: "fdfdfdf",
                    },
                ],
            };
            pyEnv.mockServer.models["helpdesk.ticket"] = {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Description", type: "char" },
                    team_id: {
                        string: "team",
                        type: "many2one",
                        relation: "helpdesk.team_id",
                    },
                    project_id: {
                        string: "Project",
                        type: "many2one",
                        relation: "project.project",
                    },
                },
                records: [
                    {
                        id: 1,
                        team_id: 1,
                        project_id: projectId5,
                        name: "fdfdfdf",
                    },
                ],
            };

            pyEnv.mockServer.models["analytic.line"].fields.helpdesk_ticket_id = {
                string: "Ticket",
                type: "many2one",
                relation: "helpdesk.ticket",
            };
        }
        return result;
    },
});
