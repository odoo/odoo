import { patch } from "@web/core/utils/patch";
import { timesheetUOMService } from "@hr_timesheet/services/timesheet_uom_service";
import { registry } from "@web/core/registry";

patch(timesheetUOMService, {
    start() {
        const service = super.start(...arguments);
        if (!registry.category("formatters").contains("timesheet_uom_timer")) {
            registry.category("formatters").add("timesheet_uom_timer", service.formatter);
        }
        return service;
    },
});
