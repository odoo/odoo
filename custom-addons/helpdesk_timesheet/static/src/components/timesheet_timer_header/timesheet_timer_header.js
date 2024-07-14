/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { TimesheetTimerHeader } from '@timesheet_grid/components/timesheet_timer_header/timesheet_timer_header';
import { useService } from "@web/core/utils/hooks";

patch(TimesheetTimerHeader.prototype, {
    setup() {
        super.setup();
        this.helpdeskTimerService = useService("helpdesk_timer_header");
    },

    /**
     * @override
     */
    async onWillStart() {
        super.onWillStart(...arguments);
        if (this.props.timerRunning && this.helpdeskTimerService.helpdeskProjects == undefined) {
            // Means helpdesk projects has not been fetched yet
            await this.helpdeskTimerService.fetchHelpdeskProjects();
        }
    },

    /**
     * @override
     */
    async onWillUpdateProps(nextProps) {
        await super.onWillUpdateProps(...arguments);
        if (nextProps.timerRunning && !nextProps.timesheet?.data?.task_id) {
            if (this.helpdeskTimerService.helpdeskProjects == undefined) {
                // Means helpdesk projects has not been fetched yet
                await this.helpdeskTimerService.fetchHelpdeskProjects();
            }
        }
    },

    get hasHelpdeskProject() {
        const project = this.props.timesheet?.data?.project_id;
        const task = this.props.timesheet?.data?.task_id;
        return !task && Boolean(project) && this.helpdeskTimerService.helpdeskProjects?.includes(project[0]);
    },
});
