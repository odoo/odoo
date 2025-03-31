/** @odoo-module **/

import { CrmKanbanModel } from "@crm/views/crm_kanban/crm_kanban_model";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class ForecastKanbanModel extends CrmKanbanModel {
    setup(params, { fillTemporalService }) {
        super.setup(...arguments);
        this.fillTemporalService = fillTemporalService;
        this.forceNextRecompute = !params.state?.groups;
        this.originalDomain = null;
        this.fillTemporalDomain = null;
    }

    async _webReadGroup(config, orderBy) {
        if (this.isForecastGroupBy(config)) {
            config.context = this.fillTemporalPeriod(config).getContext({
                context: config.context,
            });
            // Domain leaves added by the fillTemporalPeriod should be replaced
            // between 2 _webReadGroup calls, not added on top of each other.
            // Keep track of the modified domain, and if encountered in the
            // future, modify the original domain instead. It is not robust
            // against external modification of `config.domain`, but currently
            // there are only replacements except this case.
            if (!this.originalDomain || this.fillTemporalDomain !== config.domain) {
                this.originalDomain = config.domain || [];
            }
            this.fillTemporalDomain = this.fillTemporalPeriod(config).getDomain({
                domain: this.originalDomain,
                forceStartBound: false,
            });
            config.domain = this.fillTemporalDomain;
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
