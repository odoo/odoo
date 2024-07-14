/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { reactive } from "@odoo/owl";
import { session } from "@web/session";
import { TimerTimesheetGridDataPoint, TimerTimesheetGridModel } from "@timesheet_grid/views/timer_timesheet_grid/timer_timesheet_grid_model";

patch(TimerTimesheetGridDataPoint.prototype, {
    async _initialiseData() {
        await super._initialiseData();
        this.data.leaderboard = reactive({});
        this.data.leaderboardType = localStorage.getItem("leaderboardType") || "billing_rate";
    },

    async _getLeaderboardData() {
        const periodStart  = this.model.navigationInfo.periodStart.startOf("month");
        const periodEnd = periodStart.endOf("month");
        const today = this.model.today;

        if (!this.data.leaderboard.anchor || this.data.leaderboard.anchor != periodStart) {
            let data = {};
            if (this.orm.isSample) {
                data.leaderboard = [];
                data.employee_id = 1;
                data.billing_rate_target = 80;
            } else {
                data = await this.orm.call(
                    "res.company",
                    "get_timesheet_ranking_data",
                    [periodStart, periodEnd, today],
                    { context: session.user_context }
                );
            }
            this.data.leaderboard.stored_leaderboard = data.leaderboard;
            this.data.leaderboard.total_time_target = data.total_time_target;
            this.data.leaderboard.billing_rate_target = data.billing_rate_target;
            this.data.leaderboard.leaderboard = this.sortAndFilterLeaderboard(this.data.leaderboard.stored_leaderboard, this.data.leaderboardType);
            this.data.leaderboard.current_employee = this.setCurrentEmployeeIndexFromLeaderboard(this.data.leaderboard.leaderboard, data.employee_id);
            this.data.leaderboard.current_employee_id = data.employee_id;
            this.data.leaderboard.anchor = periodStart;
        }
    },

    sortAndFilterLeaderboard(array, order_by) {
        const min = order_by === "billing_rate" ? 0.5 : 0;
        array.sort((a, b) => b[order_by] - a[order_by]);
        return array.filter((line) => line[order_by] > min);
    },

    setCurrentEmployeeIndexFromLeaderboard(array, employee_id) {
        const index = array.findIndex(object => object.id === employee_id);
        if (index >= 0) {
            array[index].index = index;
        }
        return array[index];
    },

    changeLeaderboardType(type) {
        this.data.leaderboardType = type;
        localStorage.setItem("leaderboardType", type);

        this.data.leaderboard.leaderboard = this.sortAndFilterLeaderboard(this.data.leaderboard.stored_leaderboard, type);
        this.data.leaderboard.current_employee = this.setCurrentEmployeeIndexFromLeaderboard(this.data.leaderboard.leaderboard, this.data.leaderboard.current_employee_id);
    }
});

// this patch is needed because the load() method empties out the past data and prevents keeping persistent data
patch(TimerTimesheetGridModel.prototype, {
    async load() {
        const leaderboard = this.data?.leaderboard;

        await super.load(...arguments);

        if (leaderboard && leaderboard.anchor?.equals(this.navigationInfo.periodStart.startOf("month"))) {
            this.data.leaderboard = leaderboard;
        } else {
            this._dataPoint._getLeaderboardData();
        }
    }
});
