/* @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ActivityModel extends RelationalModel {
    static DEFAULT_LIMIT = 100;

    async load(params = {}) {
        this.originalDomain = params.domain ? [...params.domain] : [];
        // Ensure that only (active) records with at least one activity, "done" (archived) or not, are fetched.
        // We don't use active_test=false in the context because otherwise we would also get archived records.
        params.domain = [...params.domain, ["activity_ids.active", "in", [true, false]]];
        if (params && "groupBy" in params) {
            params.groupBy = [];
        }
        await Promise.all([this.fetchActivityData(params), super.load(params)]);
    }

    async fetchActivityData(params) {
        this.activityData = await this.orm.call("mail.activity", "get_activity_data", [], {
            res_model: this.config.resModel,
            domain: params.domain || this.env.searchModel._domain,
            limit: params.limit || this.initialLimit,
            offset: params.offset || 0,
            fetch_done: true,
        });
    }
}
