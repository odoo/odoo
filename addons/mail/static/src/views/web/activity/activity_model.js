/* @odoo-module */

import { Domain } from "@web/core/domain";
import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ActivityModel extends RelationalModel {
    static DEFAULT_LIMIT = 100;
    static SUPPORTED_FILTERS = {
        'activities_my': 'activities_my',
        'activities_overdue': 'activities_state_overdue',
        'activities_today': 'activities_state_today',
        'activities_upcoming_all': 'activities_state_planned',
    };
    static SUPPORTED_SEARCH_FIELD = new Set(
        ['activity_user_id', 'activity_create_uid', 'activity_state']);

    async load(params = {}) {
        this.originalDomain = params.domain ? [...params.domain] : [];
        const searchModel = this.env.searchModel;
        params.domain = params?.domain ?? [...(searchModel?._domain ?? [])];
        if (!params.domain.flat(Infinity).find((p) =>
            (['has_visible_activities', 'has_user_visible_activities'].includes(p)))) {
            params.domain = Domain.and([params.domain, [['has_visible_activities', '=', true]]]).toList();
        }
        if (params && "groupBy" in params) {
            params.groupBy = [];
        }
        await Promise.all([
            this.fetchActivityData({
                ...params,
                activity_filters: Array.from(new Set(searchModel.query
                    .map((query) => searchModel.searchItems[query.searchItemId])
                    .filter((searchItem) => searchItem.type === 'filter')
                    .map((searchItem) => ActivityModel.SUPPORTED_FILTERS[searchItem.name])
                    .filter((filter) => filter !== undefined))),
                activity_search_fields: searchModel.query
                    .map((query) => [searchModel.searchItems[query.searchItemId], query])
                    .filter(([searchItem, _]) => (searchItem.type === 'field') &&
                        (ActivityModel.SUPPORTED_SEARCH_FIELD.has(searchItem.fieldName)))
                    .map(([searchItem, query]) => [searchItem.fieldName, query.autocompleteValue.value])
            }),
            super.load(params)
        ]);
    }

    async fetchActivityData(params) {
        this.activityData = await this.orm.call("mail.activity", "get_activity_data", [], {
            res_model: this.config.resModel,
            domain: params.domain || this.env.searchModel._domain,
            limit: params.limit || this.initialLimit,
            offset: params.offset || 0,
            activity_filters: params.activity_filters || null,
            activity_search_fields: params.activity_search_fields || null,
        });
    }
}
