/** @odoo-module **/

import { KanbanModel } from "@web/views/kanban/kanban_model";

export class ForecastKanbanModel extends KanbanModel {
    setup(params, { fillTemporalService }) {
        super.setup(...arguments);
        this.fillTemporalService = fillTemporalService;
    }
}

export class ForecastKanbanDynamicGroupList extends ForecastKanbanModel.DynamicGroupList {
    /**
     * @override
     */
    setup(params, state) {
        super.setup(...arguments);
        // Detect a reload vs an initial load, initial load should forceRecompute
        this.forceNextRecompute = !state.groups;
    }

    /**
     * @override
     *
     * Add fill_temporal context keys to the context before loading the groups.
     */
    get context() {
        const context = super.context;
        if (!this.isForecastGroupBy()) {
            return context;
        }
        return this.fillTemporalPeriod.getContext({ context });
    }

    /**
     * return {FillTemporalPeriod} current fillTemporalPeriod according to group by state
     */
    get fillTemporalPeriod() {
        const context = super.context;
        const minGroups = (context.fill_temporal && context.fill_temporal.min_groups) || undefined;
        const { name, type, granularity } = this.groupByField;
        const forceRecompute = this.forceNextRecompute;
        this.forceNextRecompute = false;
        return this.model.fillTemporalService.getFillTemporalPeriod({
            modelName: this.resModel,
            field: {
                name,
                type,
            },
            granularity: granularity || "month",
            minGroups,
            forceRecompute,
        });
    }

    /**
     * @returns {Boolean} true if the view is grouped by the forecast_field
     */
    isForecastGroupBy() {
        const forecastField = super.context.forecast_field;
        const { name } = this.groupByField;
        return forecastField && forecastField === name;
    }

    /**
     * @override
     *
     * At every __load/__reload, we have to check the range of the last group received from the
     * read_group, and update the fillTemporalPeriod from the FillTemporalService accordingly
     */
    async load() {
        if (!this.isForecastGroupBy()) {
            return super.load(...arguments);
        }
        const result = await super.load(...arguments);
        const lastGroup = this.groups.filter((grp) => grp.value).slice(-1)[0];
        if (lastGroup) {
            this.fillTemporalPeriod.setEnd(moment.utc(lastGroup.range[this.groupBy[0]].to));
        }
        return result;
    }

    /**
     * @override
     *
     * Applies the forecast logic to the domain and context if needed before the read_group.
     */
    async _loadGroups() {
        if (!this.isForecastGroupBy()) {
            return super._loadGroups(...arguments);
        }
        const previousDomain = this.domain;
        this.domain = this.fillTemporalPeriod.getDomain({
            domain: this.domain,
            forceStartBound: false,
        });
        const result = await super._loadGroups(...arguments);
        this.domain = previousDomain;
        return result;
    }
}

ForecastKanbanModel.services = [...KanbanModel.services, "fillTemporalService"];
ForecastKanbanModel.DynamicGroupList = ForecastKanbanDynamicGroupList;
