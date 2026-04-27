/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Many2OneAvatarRankField } from "@sale_timesheet_enterprise/components/many2one_avatar_rank_field/many2one_avatar_rank_field";

import { Component, onWillStart, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
export class TimesheetLeaderboardDialog extends Component {
    static template = "sale_timesheet_enterprise.TimesheetLeaderboardDialog";
    static components = {
        Dialog,
        Many2OneAvatarRankField,
    };
    static props = {
        model: { type: Object, optional: true },
        date: { type: Object },
        close: { type: Function },
        type: { type: String },
        changeType: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.timesheetUOMService = useService("timesheet_uom");
        this.state = useState({
            date: this.props.date.startOf("month"),
            type: this.props.type,
            showAll: false,
            leaderboard: [],
            stored_leaderboard: [],
            current_employee: {},
        });

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        await this.getLeaderboardData(true);
    }

    async getLeaderboardData(fetchTip=false) {
        const periodEnd = this.state.date.endOf("month");
        const data = await this.orm.call(
            "res.company",
            "get_timesheet_ranking_data",
            [this.state.date, periodEnd, periodEnd, fetchTip],
            { context: user.context }
        );
        if (fetchTip) {
            this.tip = data.tip;
        }
        this.state.stored_leaderboard = data.leaderboard;
        this.state.leaderboard = this.sortAndFilterLeaderboard(this.state.stored_leaderboard, this.state.type);
        this.state.current_employee = this.setCurrentEmployeeIndexFromLeaderboard(this.state.leaderboard, data.employee_id);
        this.state.current_employee_id = data.employee_id;
    }

    sortAndFilterLeaderboard(array, order_by) {
        const min = order_by === "billing_rate" ? 0.5 : 0;
        array.sort((a, b) => b[order_by] - a[order_by]);
        return array.filter((line) => line[order_by] > min);
    }

    setCurrentEmployeeIndexFromLeaderboard(array, employee_id) {
        const index = array.findIndex(object => object.id === employee_id);
        if (index >= 0) {
            array[index].index = index;
        }
        return array[index] || {};
    }

    changeType(type) {
        this.props.changeType(type);
        this.state.type = type;
        this.state.leaderboard = this.sortAndFilterLeaderboard(this.state.stored_leaderboard, type);
        this.state.current_employee = this.setCurrentEmployeeIndexFromLeaderboard(this.state.leaderboard, this.state.current_employee_id)
    }

    async goNextMonth() {
        this.state.date = this.state.date.plus({ month: 1 })
        this.getLeaderboardData();
    }

    async goLastMonth() {
        this.state.date = this.state.date.minus({ month: 1 })
        this.getLeaderboardData();
    }

    async goCurrentMonth() {
        this.state.date = this.props.date;
        this.getLeaderboardData();
    }

    async onKeyUp(ev) {
        switch (ev.key) {
            case "ArrowRight":
                await this.goNextMonth();
                break;
            case "ArrowLeft":
                await this.goLastMonth();
                break;
            case "ArrowDown":
                await this.goCurrentMonth();
                break;
            case "t":
                this.changeType(this.state.type === "billing_rate" ? "total_time" : "billing_rate");
                break;
        }
    }

    getBillingRateText(employee) {
        return _t("%(billableTime)s / %(billable_time_target)s (%(billingRate)s%)", {
            billableTime: this.format(employee.billable_time),
            billable_time_target: this.format(employee.billable_time_target),
            billingRate: Math.round(employee.billing_rate),
        });
    }

    getTotalTimeText(employee) {
        return _t("Total: %(totalTime)s", {
            totalTime: this.format(employee.total_time),
        });
    }

    getTitle(type) {
        return type === "billing_rate" ? _t("Billing Rate Leaderboard") : _t("Total Time Leaderboard");
    }

    get displayLimit() {
        return this.state.showAll ? Infinity : 10;
    }

    get isMobile() {
        return this.env.isSmall;
    }

    get currentFormattedDate() {
        return this.state.date.setLocale(user.lang).toLocaleString({
            year: "numeric",
            month: "long",
        });
    }

    format(value) {
        return this.timesheetUOMService.formatter(value, {
            noLeadingZeroHour: true,
        }).replace(/(:|\.)00/g, "");
    }
}
