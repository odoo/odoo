/* @odoo-module */

import { DataPoint } from "./datapoint";

const AGGREGATABLE_FIELD_TYPES = ["float", "integer", "monetary"]; // types that can be aggregated in grouped views

export class Group extends DataPoint {
    setup(params) {
        super.setup();
        this.groupByField = this.fields[params.groupByFieldName];
        this.progressBars = []; // FIXME: remove from model?
        this.tooltip = []; // FIXME: remove from model?
        const groupData = params.data;
        this.isFolded = groupData.__fold || false;
        // this.range = groupData.__range;
        // this.__rawValue = groupData[this.groupByField.name]; // might be useful at some point
        // When group_by_no_leaf key is present FIELD_ID_count doesn't exist
        // we have to get the count from `__count` instead
        // see _read_group_raw in models.py
        this.count = groupData.__count || groupData[`${this.groupByField.name}_count`] || 0;
        this.value = this._getValueFromGroupData(groupData, this.groupByField);
        this.displayName = this._getDisplayNameFromGroupData(groupData, this.groupByField);
        this.aggregates = this._getAggregatesFromGroupData(groupData);
        const listParams = {
            activeFields: this.activeFields,
            fields: this.fields,
            resModel: this.resModel,
            context: this.context,
            groupBy: params.groupBy,
            domain: groupData.__domain,
        };
        if (params.groupBy.length) {
            this.list = new this.model.constructor.DynamicGroupList(this.model, {
                ...listParams,
                data: { count: this.count, groups: groupData.groups },
            });
        } else {
            this.list = new this.model.constructor.DynamicRecordList(this.model, {
                ...listParams,
                data: { count: this.count, records: groupData.records },
            });
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get records() {
        return this.list.records;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    async toggle() {
        this.isFolded = !this.isFolded;
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    /**
     * @param {Object} groupData
     * @returns {Object}
     */
    _getAggregatesFromGroupData(groupData) {
        const aggregates = {};
        for (const [key, value] of Object.entries(groupData)) {
            if (key in this.fields && AGGREGATABLE_FIELD_TYPES.includes(this.fields[key].type)) {
                aggregates[key] = value;
            }
        }
        return aggregates;
    }

    /**
     * @param {Object} groupData
     * @param {Object} field
     * @returns {string | false}
     */
    _getDisplayNameFromGroupData(groupData, field) {
        if (field.type === "selection") {
            return Object.fromEntries(field.selection)[groupData[field.name]];
        }
        if (["many2one", "many2many"].includes(field.type)) {
            return groupData[field.name] ? groupData[field.name][1] : false;
        }
        return groupData[field.name];
    }

    /**
     * @param {Object} groupData
     * @param {Object} field
     * @returns {any}
     */
    _getValueFromGroupData(groupData, field) {
        if (["date", "datetime"].includes(field.type)) {
            const range = groupData.__range[field.name];
            if (!range) {
                return false;
            }
            const dateValue = this._parseServerValue(field, range.to);
            return dateValue.minus({
                [field.type === "date" ? "day" : "second"]: 1,
            });
        }
        const value = this._parseServerValue(field, groupData[field.name]);
        if (["many2one", "many2many"].includes(field.type)) {
            return value ? value[0] : false;
        }
        return value;
    }
}
