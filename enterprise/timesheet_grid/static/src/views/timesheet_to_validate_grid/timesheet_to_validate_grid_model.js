import { browser } from "@web/core/browser/browser";
import { TimesheetGridModel } from "../timesheet_grid/timesheet_grid_model";

export class TimesheetToValidateGridModel extends TimesheetGridModel {
    setup(params) {
        const activeRangeName = browser.localStorage.getItem(this.storageKey) || params.activeRangeName;
        const range = params.ranges[activeRangeName];
        params.defaultAnchor = this.today.minus({
            [range.span]: 1,
        });
        super.setup(params);
    }
}
