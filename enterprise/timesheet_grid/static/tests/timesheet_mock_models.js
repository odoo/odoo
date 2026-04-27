import { serializeDateTime } from "@web/core/l10n/dates";
import { PyDate } from "@web/core/py_js/py_date";
import { defineModels, models, fields } from "@web/../tests/web_test_helpers";

import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";
import { projectModels } from "@project/../tests/project_models";

export class AnalyticLine extends models.Model {
    _name = "account.analytic.line";

    name = fields.Char();
    date = fields.Date({ default: PyDate.today().strftime("%Y-%m-%d") });
    unit_amount = fields.Float();
    project_id = fields.Many2one({ relation: "project.project" });
    task_id = fields.Many2one({ relation: "project.task" });
    employee_id = fields.Many2one({ relation: "hr.employee" });
    display_timer = fields.Boolean();
    is_timesheet = fields.Boolean();
    timer_start = fields.Datetime();
    company_id = fields.Many2one({ relation: "res.company" });

    action_start_new_timesheet_timer(...args) {
        const timesheet = this.create({
            project_id: false,
        });

        // Creating a timer to run usally done "timer.mixin"
        const timer = this.env["timer.timer"].create({
            timer_start: false,
            timer_pause: false,
            is_timer_running: false,
            res_model: this._name,
            res_id: timesheet,
            user_id: this.env.user.id,
        });
        this.env["timer.timer"].action_timer_start(timer);

        return { id: timer };
    }
}

export class TimerTimer extends models.Model {
    _name = "timer.timer";

    timer_start = fields.Datetime();
    timer_pause = fields.Datetime();
    is_timer_running = fields.Boolean();
    res_model = fields.Char();
    res_id = fields.Integer();
    user_id = fields.Many2one({ relation: "res.users" });

    action_timer_start(...args) {
        if (!this.read(args[0], ["timer_start"])[0].timer_start) {
            this.write(args[0], {
                timer_start: serializeDateTime(luxon.DateTime.now().setZone("utc")),
            });
        }
    }
}

export function defineTimesheetModels() {
    defineMailModels();
    defineModels(timesheetModels);
}

export const timesheetModels = {
    ...projectModels,
    AnalyticLine,
    TimerTimer,
    HrEmployee,
};
