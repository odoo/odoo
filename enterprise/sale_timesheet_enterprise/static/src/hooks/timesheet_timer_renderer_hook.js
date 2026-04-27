/** @odoo-module */

import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

import { TimesheetTimerRendererHook } from "@timesheet_grid/hooks/timesheet_timer_hooks";

const { DateTime } = luxon;

patch(TimesheetTimerRendererHook.prototype, {
    setup() {
        super.setup();
        if (!browser.localStorage.getItem("leaderboardType")) {
            browser.localStorage.setItem("leaderboardType", "billing_rate");
        }
        this.leaderboardType = browser.localStorage.getItem("leaderboardType");
        this.leaderboard = reactive({});
    },

    async onWillStart() {
        await super.onWillStart();
        this._getLeaderboardData();
    },

    async _getLeaderboardData() {
        const today = DateTime.local().startOf("day");
        const periodStart = today.startOf("month");
        const periodEnd = today.endOf("month");

        const data = await this.orm.call(
            "res.company",
            "get_timesheet_ranking_data",
            [periodStart, periodEnd, today, false],
            { context: user.context }
        );
        this.leaderboard.show_leaderboard = data.show_leaderboard;
        this.leaderboard.total_time_target = data.total_time_target;
        this.leaderboard.stored_leaderboard = data.leaderboard;
        this.leaderboard.leaderboard = this._sortAndFilterLeaderboard(this.leaderboard.stored_leaderboard, this.leaderboardType);
        this.leaderboard.current_employee = this._setCurrentEmployeeIndexFromLeaderboard(this.leaderboard.leaderboard, data.employee_id);
        this.leaderboard.current_employee_id = data.employee_id;
    },

    _sortAndFilterLeaderboard(array, order_by) {
        const min = order_by === "billing_rate" ? 0.5 : 0;
        array.sort((a, b) => b[order_by] - a[order_by]);
        return array.filter((line) => line[order_by] > min);
    },

    _setCurrentEmployeeIndexFromLeaderboard(array, employee_id) {
        const index = array.findIndex(object => object.id === employee_id);
        if (index >= 0) {
            array[index].index = index;
        }
        return array[index];
    },

    changeLeaderboardType(type) {
        this.leaderboardType = type;
        browser.localStorage.setItem("leaderboardType", type);
        this.leaderboard.leaderboard = this._sortAndFilterLeaderboard(this.leaderboard.stored_leaderboard, type);
        this.leaderboard.current_employee = this._setCurrentEmployeeIndexFromLeaderboard(this.leaderboard.leaderboard, this.leaderboard.current_employee_id);

    },
});
