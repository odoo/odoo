/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { isDateField, normalizeServerValue, parseGroupField } from "./pivot_utils";

patch(PivotModel.prototype, {
    setup(params) {
        super.setup(params);
        /**
         * Mapping `[groupBy][dateValueInReadGroup]: normalizedDateValue`.
         *
         * The mapping is useful because it's not always possible to transform on the fly a string date that was obtained
         * from a read_group into a normalized date value (because the read_group dates strings are localized).
         *
         * @example
         * {
         *   "create_date:day": {
         *       "12 Nov 2023": "11/12/2023",
         *       "30 Dec 2024": "12/30/2024",
         *   },
         *   "date_deadline:month": {
         *       "March 2020":   "03/2020",
         *       "January 2022": "01/2022",
         *   }
         * }
         */
        this._readGroupDateValuesMapping = {};
    },
    /**
     * @override
     * Override _prepareData to build the mapping "readGroupDates" <-> "normalizedDates"
     */
    _prepareData(rootGroup, groupSubdivisions, config) {
        for (const groupSubdivision of groupSubdivisions) {
            for (const subGroup of groupSubdivision.subGroups) {
                this._buildReadGroupDateMapping(subGroup, groupSubdivision.rowGroupBy);
                this._buildReadGroupDateMapping(subGroup, groupSubdivision.colGroupBy);
            }
        }
        super._prepareData(rootGroup, groupSubdivisions, config);
    },
    _buildReadGroupDateMapping(group, groupBys) {
        for (const groupBy of groupBys) {
            const { field, aggregateOperator } = parseGroupField(this.metaData.fields, groupBy);
            if (isDateField(field)) {
                const normalized = normalizeServerValue(aggregateOperator, groupBy, field, group);

                if (!this._readGroupDateValuesMapping[groupBy]) {
                    this._readGroupDateValuesMapping[groupBy] = {};
                }
                this._readGroupDateValuesMapping[groupBy][group[groupBy]] = normalized.toString();
            }
        }
    },
    _getNormalizedDateValueFromReadGroupDate(groupBy, date) {
        if (date === false) {
            return date;
        }
        if (groupBy.startsWith("#")) {
            groupBy = groupBy.slice(1);
        }
        return this._readGroupDateValuesMapping[groupBy][date];
    },
    _getReadGroupDateValueFromNormalizedDate(groupBy, normalizedDate) {
        if (normalizedDate === false) {
            return normalizedDate;
        }
        if (groupBy.startsWith("#")) {
            groupBy = groupBy.slice(1);
        }
        const normalizedDateString = normalizedDate.toString();
        const values = this._readGroupDateValuesMapping[groupBy];
        return Object.keys(values).find((key) => values[key] === normalizedDateString);
    },
    getNormalizedSortedColumn() {
        return this._normalizeOrLocalizeSortedColumn(this.metaData.sortedColumn, "normalize");
    },
    _localizeSortedColumn(normalizedSortedColumn) {
        return (
            this._normalizeOrLocalizeSortedColumn(normalizedSortedColumn, "localize") ||
            normalizedSortedColumn
        );
    },
    _normalizeOrLocalizeSortedColumn(sortedColumn, mode) {
        if (!sortedColumn) {
            return undefined;
        }
        const sortColumnValues = [];
        for (let i = 0; i < this.metaData.fullColGroupBys.length; i++) {
            const groupBy = this.metaData.fullColGroupBys[i];
            let sortValue = sortedColumn.groupId[1][i];
            const { field } = parseGroupField(this.metaData.fields, groupBy);
            if (isDateField(field)) {
                sortValue =
                    mode === "localize"
                        ? this._getReadGroupDateValueFromNormalizedDate(groupBy, sortValue)
                        : this._getNormalizedDateValueFromReadGroupDate(groupBy, sortValue);
                if (sortValue === undefined) {
                    return undefined;
                }
            }
            sortColumnValues.push(sortValue);
        }
        return {
            ...sortedColumn,
            groupId: [sortedColumn.groupId[0], sortColumnValues],
        };
    },
});
