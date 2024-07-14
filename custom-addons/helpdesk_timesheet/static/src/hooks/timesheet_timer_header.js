/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { TimesheetTimerRendererHook } from "@timesheet_grid/hooks/timesheet_timer_hooks";

patch(TimesheetTimerRendererHook.prototype, {
    setup() {
        super.setup();
        this.helpdeskTimerHeaderService = useService("helpdesk_timer_header");
    },

    onWillUnmount() {
        super.onWillUnmount();
        this.helpdeskTimerHeaderService.invalidateCache();
    },
});
