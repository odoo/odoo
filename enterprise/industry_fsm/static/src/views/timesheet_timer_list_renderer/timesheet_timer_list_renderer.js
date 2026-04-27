import { onWillStart } from "@odoo/owl";
import { TimesheetTimerListRenderer } from "@timesheet_grid/views/timesheet_list/timesheet_timer_list_renderer";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(TimesheetTimerListRenderer.prototype, {
    setup() {
        super.setup();
        this.createEditProjectIdsService = useService("create_edit_project_ids");
        onWillStart(async () => {
            await this.createEditProjectIdsService.fetchProjectIds();
        });
    },
});
