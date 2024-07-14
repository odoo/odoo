/** @odoo-module */

import { CalendarModel } from "@web/views/calendar/calendar_model";
import { usePlanningModelActions } from "../planning_hooks";
import { _t } from "@web/core/l10n/translation";

export class PlanningCalendarModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        this.getHighlightIds = usePlanningModelActions({
            getHighlightPlannedIds: () => this.env.searchModel.highlightPlannedIds,
            getContext: () => this.env.searchModel._context,
        }).getHighlightIds;
    }

    get defaultFilterLabel() {
        return _t("Open Shifts");
    }

    /**
     * @override
     */
    addFilterFields(record, filterInfo) {
        // For 'Resource' filters we need the resource_color for the colorIndex, for 'Role' filters we need the colorIndex
        if (filterInfo.fieldName == 'resource_id') {
            return {
                colorIndex: record.rawRecord.resource_type == 'material' ? record.rawRecord['resource_color'] : '',
                resourceType: record.rawRecord['resource_type'],
            };
        }
        return {
            ...super.addFilterFields(record, filterInfo),
            resourceType: record.rawRecord['resource_type'],
        };
    }

    /**
     * @override
     */
    async loadRecords(data) {
        this.highlightIds = await this.getHighlightIds();
        return await super.loadRecords(data);
    }

    /**
     * @override
     */
    makeFilterDynamic(filterInfo, previousFilter, fieldName, rawFilter, rawColors) {
        return {
            ...super.makeFilterDynamic(filterInfo, previousFilter, fieldName, rawFilter, rawColors),
            resourceType: rawFilter['resourceType'],
            colorIndex: rawFilter['colorIndex'],
        };
    }

    /**
     * @override
     */
    makeContextDefaults(rawRecord) {
        const context = super.makeContextDefaults(...arguments);
        if (["day", "week"].includes(this.meta.scale)) {
            context['planning_keep_default_datetime'] = true;
        }
        return context;
    }
}
