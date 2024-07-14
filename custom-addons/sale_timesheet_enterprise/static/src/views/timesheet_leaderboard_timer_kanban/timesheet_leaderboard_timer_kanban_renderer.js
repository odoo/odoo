/** @odoo-module **/

import { TimesheetTimerKanbanRenderer } from "@timesheet_grid/views/timesheet_kanban/timesheet_timer_kanban_renderer";
import { TimesheetLeaderboard } from "@sale_timesheet_enterprise/components/timesheet_leaderboard/timesheet_leaderboard";

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

patch(TimesheetTimerKanbanRenderer, {
    components: {
        ...TimesheetTimerKanbanRenderer.components,
        TimesheetLeaderboard,
    },
});

patch(TimesheetTimerKanbanRenderer.prototype, {
    setup() {
        super.setup()
        this.user = useService('user');
        this.orm = useService('orm');
        onWillStart(this.onWillStart);
    },

    async onWillStart() {
        this.userHasBillingRateGroup = await this.user.hasGroup('sale_timesheet_enterprise.group_timesheet_leaderboard_show_rates');
        const result = await this.orm.call('hr.employee', 'get_billable_time_target', [[this.user.userId]]);
        const billableTimeTarget = result.length ? result[0].billable_time_target : 0;
        this.showIndicators = billableTimeTarget > 0;
        this.showLeaderboard = await this.user.hasGroup('sale_timesheet_enterprise.group_use_timesheet_leaderboard');
        this.showLeaderboardComponent = (this.userHasBillingRateGroup && this.showIndicators) || this.showLeaderboard;
    },

    get isMobile() {
        return this.env.isSmall;
    },
});
