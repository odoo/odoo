/** @odoo-module */

import { RelationalModel } from "@web/views/relational_model";

export class ActivityModel extends RelationalModel {
    async load(params = {}) {
        this.activityData = await this.fetchActivityData(params);
        await super.load(params);
    }

    fetchActivityData(params) {
        return this.orm.call("mail.activity", "get_activity_data", [], {
            res_model: this.rootParams.resModel,
            domain: params.domain || this.env.searchModel._domain,
        });
    }
}
