import { TimesheetListRenderer} from "@hr_timesheet/views/timesheet_list/timesheet_list_renderer";
import { patch } from "@web/core/utils/patch";

patch(TimesheetListRenderer.prototype, {
    setup()
    {
        super.setup();
        this.multiEditBlackList.push("so_line");
    }
});
