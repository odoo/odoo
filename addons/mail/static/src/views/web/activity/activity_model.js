/* @odoo-module */

import { DynamicRecordList, RelationalModel } from "@web/views/relational_model";

class ActivityDynamicRecordList extends DynamicRecordList {
    setup() {
        super.setup(...arguments);
        this.limit = null;
    }
}
export class ActivityModel extends RelationalModel {
    static DynamicRecordList = ActivityDynamicRecordList;

    async load(params = {}) {
        this.originalDomain = params.domain ? [...params.domain] : [];
        params.domain = [...(params.domain || []), ["activity_ids", "!=", false]];
        if (params && "groupBy" in params) {
            params.groupBy = [];
        }
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
