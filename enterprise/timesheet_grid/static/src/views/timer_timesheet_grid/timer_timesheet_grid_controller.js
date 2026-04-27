/** @odoo-module */

import { useSubEnv } from "@odoo/owl";

import { TimesheetGridController } from "../timesheet_grid/timesheet_grid_controller";

export class TimerTimesheetGridController extends TimesheetGridController {
    setup() {
        super.setup();
        useSubEnv({
            config: {
                ...this.env.config,
                disableSearchBarAutofocus: true,
            },
        });
    }

    get displayAddALine() {
        // display `Add a line` button si create inline is disabled or if there is no content
        return super.displayAddALine && (!this.props.archInfo.createInline || this.displayNoContent);
    }
}
