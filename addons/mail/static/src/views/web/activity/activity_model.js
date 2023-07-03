/* @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ActivityModel extends RelationalModel {
    static DEFAULT_LIMIT = 100;

    async load(params = {}) {
        this.originalDomain = params.domain ? [...params.domain] : [];
        params.domain = params?.domain ?? [...(this.env.searchModel?._domain ?? [])];
        if (!params.domain.flat(Infinity).find((p) =>
            (['has_visible_activities', 'has_user_visible_activities'].includes(p)))) {
            params.domain.push(['has_visible_activities', '=', true]);
        }
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
        });
    }
}
