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

    /**
     * Extracts pagination parameters 'limit' and 'offset' from params and return them along with the rest of the params
     * properties.
     *
     * If 'limit' and/or 'offset' are not found in the object, default values are set (80 for limit, 0 for offset).
     *
     * @param params search parameters
     * @returns {{paramsWithoutPagination: Object, offset: number, limit: number}}
     * @private
     */
    static _extractPaginationParams(params) {
        const paramsWithoutPagination = {...params};
        let limit = 80; // default limit
        if ('limit' in paramsWithoutPagination) {
            limit = paramsWithoutPagination.limit;
            delete paramsWithoutPagination.limit;
        }
        let offset = 0;
        if ('offset' in paramsWithoutPagination) {
            offset = paramsWithoutPagination.offset;
            delete paramsWithoutPagination.offset;
        }
        return {paramsWithoutPagination:paramsWithoutPagination, offset:offset, limit:limit};
    }

    /**
     * Loads model instances linked to the loaded activities (activityData).
     *
     * For example, for event activities, loads the event.event instance related to the activities.
     *
     * @param params search parameters
     * @returns {Promise<void>}
     */
    async loadRelatedModel(params){
        const { paramsWithoutPagination, offset, limit } = ActivityModel._extractPaginationParams(params);
        if ( (limit) && (this.activityData.activity_res_ids.length > limit) ) {
            const selectedIds = this.activityData.activity_res_ids.slice(offset, offset + limit);
            if (!paramsWithoutPagination.domain) {
                paramsWithoutPagination.domain = [];
            }
            paramsWithoutPagination.domain.push(["id", "in", selectedIds]);
        }
        await super.load(paramsWithoutPagination);
        this.offset = offset;
        this.limit = limit;
    }

    async load(params = {}) {
        this.originalDomain = params.domain ? [...params.domain] : [];
        params.domain?.push(["activity_ids", "!=", false]);
        if (params && "groupBy" in params) {
            params.groupBy = [];
        }
        const { paramsWithoutPagination, offset, limit } = ActivityModel._extractPaginationParams(params);
        this.activityData = await this.fetchActivityData(paramsWithoutPagination);
        await this.loadRelatedModel({ ...paramsWithoutPagination, offset: offset, limit: limit });
    }

    fetchActivityData(params) {
        return this.orm.call("mail.activity", "get_activity_data", [], {
            res_model: this.rootParams.resModel,
            domain: params.domain || this.env.searchModel._domain,
        });
    }
}
