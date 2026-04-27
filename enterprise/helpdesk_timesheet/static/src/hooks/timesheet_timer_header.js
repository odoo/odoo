/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { TimesheetTimerRendererHook } from "@timesheet_grid/hooks/timesheet_timer_hooks";
import { TimesheetTimerListController } from "@timesheet_grid/views/timesheet_list/timesheet_timer_list_controller";
import { TimesheetTimerKanbanController } from "@timesheet_grid/views/timesheet_kanban/timesheet_timer_kanban_controller";

patch(TimesheetTimerRendererHook.prototype, {
    setup() {
        super.setup();
        this.helpdeskTimerHeaderService = useService("helpdesk_timer_header");
    },

    async onWillStart() {
        await super.onWillStart();
        this.helpdeskTimerHeaderService.invalidateCache();
    },
});

const patchController = () => ({
    onChangeWriteValues(record) {
        const { helpdesk_ticket_id } = record._getChanges();
        return {
            ...super.onChangeWriteValues(record),
            helpdesk_ticket_id,
        };
    },
});

patch(TimesheetTimerListController.prototype, patchController());
patch(TimesheetTimerKanbanController.prototype, patchController());
