/** @odoo-module */

import { serializeDate, deserializeDate } from "@web/core/l10n/dates";
import { GridNavigationInfo, GridModel, GridDataPoint } from "@web_grid/views/grid_model";

export class AnalyticLineGridDataPoint extends GridDataPoint {
    async _initialiseData() {
        if (this.navigationInfo.range.span === "year") {
            await this.navigationInfo.fetchPeriod();
        }
        await super._initialiseData();
    }
}

export class AnalyticLineGridNavigationInfo extends GridNavigationInfo {
    get periodStart() {
        if (this.range.span !== "year" || !this._periodStart) {
            return super.periodStart;
        }
        return this._periodStart;
    }

    get periodEnd() {
        if (this.range.span !== "year" || !this._periodEnd) {
            return super.periodEnd;
        }
        return this._periodEnd;
    }

    async fetchPeriod() {
        const { date_from, date_to } = await this.model.orm.call(
            this.model.resModel,
            "grid_compute_year_range",
            [serializeDate(this.anchor)]
        );
        this._periodStart = deserializeDate(date_from);
        this._periodEnd = deserializeDate(date_to);
    }
}

export class AnalyticLineGridModel extends GridModel {
    static DataPoint = AnalyticLineGridDataPoint;
    static NavigationInfo = AnalyticLineGridNavigationInfo;
}
