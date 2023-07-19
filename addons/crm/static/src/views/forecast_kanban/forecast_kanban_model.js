/** @odoo-module **/

import { CrmKanbanModel } from "@crm/views/crm_kanban/crm_kanban_model";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class ForecastKanbanModel extends CrmKanbanModel {
    setup(params, { fillTemporalService }) {
        super.setup(...arguments);
        this.fillTemporalService = fillTemporalService;
        this.forceNextRecompute = !params.state?.groups;
    }

    async _webReadGroup(config, firstGroupByName, orderBy) {
        if (this.isForecastGroupBy(config)) {
            config.context = this.fillTemporalPeriod(config).getContext({
                context: config.context,
            });
            config.domain = this.fillTemporalPeriod(config).getDomain({
                        domain: config.domain,
                        forceStartBound: false,
                    });
        }
        return super._webReadGroup(...arguments);
    }

    async _loadGroupedList(config) {
        const res = await super._loadGroupedList(...arguments);
        if (this.isForecastGroupBy(config)) {
            const lastGroup = res.groups.filter((grp) => grp.value).slice(-1)[0];
            if (lastGroup) {
                this.fillTemporalPeriod(config).setEnd(deserializeDateTime(lastGroup.range.to));
            }
        }
        return res;
    }

    /**
     * @returns {Boolean} true if the view is grouped by the forecast_field
     */
    isForecastGroupBy(config) {
        const forecastField = config.context.forecast_field;
        const name = config.groupBy[0].split(":")[0];
        return forecastField && forecastField === name;
    }

    /**
     * return {FillTemporalPeriod} current fillTemporalPeriod according to group by state
     */
    fillTemporalPeriod(config) {
        const [groupByFieldName, granularity] = config.groupBy[0].split(":");
        const groupByField = config.fields[groupByFieldName];
        const minGroups = (config.context.fill_temporal && config.context.fill_temporal.min_groups) || undefined;
        const { name, type } = groupByField;
        const forceRecompute = this.forceNextRecompute;
        this.forceNextRecompute = false;
        return this.fillTemporalService.getFillTemporalPeriod({
            modelName: config.resModel,
            field: {
                name,
                type,
            },
            granularity: granularity || "month",
            minGroups,
            forceRecompute,
        });
    }
}

ForecastKanbanModel.services = [...CrmKanbanModel.services, "fillTemporalService"];
