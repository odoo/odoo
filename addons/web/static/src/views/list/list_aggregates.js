// @ts-check

/** @module @web/views/list/list_aggregates - Hook computing column aggregates and multi-currency popovers for the list view */

/** @odoo-module **/

import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AGGREGATABLE_FIELD_TYPES } from "@web/model/relational_model/utils";
import { getCurrencyRates } from "@web/services/currency";
import { user } from "@web/services/user";
import { usePopover } from "@web/ui/popover/popover_hook";
import { MultiCurrencyPopover } from "@web/views/view_components/multi_currency_popover";
import { computeAggregatedValue } from "@web/views/view_measurements";

const formatters = registry.category("formatters");

/**
 * Determine which currency field is associated with a monetary column.
 *
 * @param {Record<string, object>} fields
 * @param {object} column
 * @returns {string}
 */
function resolveCurrencyField(fields, column) {
    return (
        column.options.currency_field ||
        fields[column.name].currency_field ||
        "currency_id"
    );
}

/**
 * Hook encapsulating aggregate computation and multi-currency popover for the list view.
 *
 * @param {object} options
 * @param {() => import("./list_renderer").Column[]} options.getColumns - active columns
 * @param {() => Record<string, object>} options.getFields - field definitions
 * @param {() => import("./list_renderer").ListRendererProps} options.getProps - component props
 * @param {() => Record<string, boolean>} options.getOptionalActiveFields
 * @returns {{
 *   computeAggregates: () => Record<string, object>,
 *   formatGroupAggregate: (group: object, column: object) => object,
 *   getFieldCurrencies: (fieldName: string) => Set,
 *   getCurrencyField: (column: object) => string,
 *   openMultiCurrencyPopover: (ev: Event, value: any, fieldName: string) => void,
 *   state: { currencyRates: object | null },
 * }}
 */
export function useListAggregates({
    getColumns,
    getFields,
    getProps,
    getOptionalActiveFields,
}) {
    const multiCurrencyPopover = usePopover(MultiCurrencyPopover, {
        position: "right",
    });
    const state = useState({ currencyRates: null });

    onWillStart(async () => {
        const props = getProps();
        const fields = getFields();
        const needsCurrencyRates = /** @type {any} */ (props).archInfo.columns.some(
            (/** @type {any} */ column) => {
                if (column.type !== "field") {
                    return false;
                }
                const field = fields[column.name];
                if (field.type !== "monetary" && column.widget !== "monetary") {
                    return false;
                }
                const currencyField = resolveCurrencyField(fields, column);
                if (!(currencyField in props.list.activeFields)) {
                    return false;
                }
                return ["sum", "avg", "max", "min"].some((agg) => agg in column.attrs);
            },
        );
        if (needsCurrencyRates) {
            state.currencyRates = await getCurrencyRates();
        }
    });

    /**
     * Get the values list appropriate for aggregation (selection, groups, or all records).
     */
    function getAggregationValues() {
        const { list } = getProps();
        if (list.selection.length) {
            return list.selection.map((r) => r.data);
        }
        if (/** @type {any} */ (list).isGrouped) {
            return /** @type {any} */ (list).groups.map(
                (/** @type {any} */ g) => g.aggregates,
            );
        }
        return list.records.map((r) => r.data);
    }

    const self = {
        state,

        /**
         * Determine which currency field is associated with a monetary column.
         *
         * @param {object} column
         * @returns {string}
         */
        getCurrencyField(column) {
            return resolveCurrencyField(getFields(), column);
        },

        /**
         * Collect the set of distinct currency IDs used for a given field.
         *
         * @param {string} fieldName
         * @returns {Set}
         */
        getFieldCurrencies(fieldName) {
            const columns = getColumns();
            const column = columns.find((c) => c.name === fieldName);
            const currencyField = self.getCurrencyField(column);
            const values = getAggregationValues();
            const { list } = getProps();
            if (/** @type {any} */ (list).isGrouped && !list.selection.length) {
                return values.reduce((set, value) => {
                    value[currencyField].forEach((c) => set.add(c));
                    return set;
                }, new Set());
            }
            return values.reduce(
                (set, value) => set.add(value[currencyField]?.id),
                new Set(),
            );
        },

        /**
         * Compute aggregate values for all visible columns.
         *
         * @returns {Record<string, object>}
         */
        computeAggregates() {
            const values = getAggregationValues();
            const columns = getColumns();
            const fields = getFields();
            const optionalActiveFields = getOptionalActiveFields();
            const { list } = getProps();
            const aggregates = {};

            for (const column of columns) {
                if (column.type !== "field") {
                    continue;
                }
                const fieldName = column.name;
                if (
                    fieldName in optionalActiveFields &&
                    !optionalActiveFields[fieldName]
                ) {
                    continue;
                }
                const field = fields[fieldName];
                const fieldValues = values
                    .map((v) => v[fieldName])
                    .filter((v) => v || v === 0);
                if (!fieldValues.length) {
                    continue;
                }
                const type = field.type;
                if (!AGGREGATABLE_FIELD_TYPES.includes(type)) {
                    continue;
                }
                const { attrs, widget } = column;
                const func =
                    (attrs.sum && "sum") ||
                    (attrs.avg && "avg") ||
                    (attrs.max && "max") ||
                    (attrs.min && "min");
                let currencyId;
                let multiCurrency = false;
                if (type === "monetary" || widget === "monetary") {
                    const currencyField = self.getCurrencyField(column);
                    if (currencyField in list.activeFields) {
                        if (
                            /** @type {any} */ (list).isGrouped &&
                            !list.selection.length
                        ) {
                            currencyId = values.find((v) => v[currencyField]?.length)?.[
                                currencyField
                            ][0];
                        } else {
                            currencyId =
                                values[0][currencyField] && values[0][currencyField].id;
                        }
                        if (func && type === "monetary") {
                            const currencies = self.getFieldCurrencies(fieldName);
                            if (currencies.size > 1) {
                                multiCurrency = true;
                                currencyId = user.activeCompany.currency_id;
                                for (const i in values) {
                                    let currency = values[i][currencyField].id;
                                    if (
                                        /** @type {any} */ (list).isGrouped &&
                                        !list.selection.length
                                    ) {
                                        currency =
                                            values[i][currencyField].length > 1
                                                ? currencyId
                                                : values[i][currencyField][0];
                                    }
                                    if (currency !== currencyId) {
                                        fieldValues[i] *= state.currencyRates[currency];
                                    }
                                }
                            }
                        }
                    }
                }
                if (func) {
                    const aggregatedValue = computeAggregatedValue(fieldValues, func);
                    const formatter =
                        formatters.get(
                            /** @type {string} */ (widget),
                            /** @type {any} */ (false),
                        ) || formatters.get(type, /** @type {any} */ (false));
                    const formatOptions = {
                        digits: attrs.digits
                            ? JSON.parse(/** @type {string} */ (attrs.digits))
                            : undefined,
                        escape: true,
                    };
                    if (currencyId) {
                        formatOptions.currencyId = currencyId;
                    }
                    aggregates[fieldName] = {
                        help: multiCurrency ? "" : attrs[func],
                        value: formatter
                            ? formatter(aggregatedValue, formatOptions)
                            : aggregatedValue,
                        multiCurrency,
                        rawValue: aggregatedValue,
                    };
                }
            }
            return aggregates;
        },

        /**
         * Format aggregate value for a group row.
         *
         * @param {object} group
         * @param {object} column
         * @returns {{ value: string, multiCurrency?: boolean, rawValue?: number }}
         */
        formatGroupAggregate(group, column) {
            const { widget, attrs } = column;
            const fields = getFields();
            const field = fields[column.name];
            const aggregateValue = group.aggregates[column.name];
            if (
                !(column.name in group.aggregates) ||
                widget === "handle" ||
                !AGGREGATABLE_FIELD_TYPES.includes(field.type)
            ) {
                return { value: "" };
            }
            const formatter =
                formatters.get(
                    /** @type {string} */ (widget),
                    /** @type {any} */ (false),
                ) || formatters.get(field.type, /** @type {any} */ (false));
            const formatOptions = {
                digits: attrs.digits
                    ? JSON.parse(/** @type {string} */ (attrs.digits))
                    : field.digits,
                escape: true,
            };
            if (field.type === "monetary") {
                const currencies = group.aggregates[field.currency_field];
                if (currencies.length > 1 && aggregateValue !== false) {
                    formatOptions.currencyId = user.activeCompany.currency_id;
                    return {
                        value: formatter
                            ? formatter(aggregateValue, formatOptions)
                            : aggregateValue,
                        multiCurrency: true,
                        rawValue: aggregateValue,
                    };
                }
                formatOptions.currencyId = currencies[0];
            }
            return {
                value: formatter
                    ? formatter(aggregateValue, formatOptions)
                    : aggregateValue,
            };
        },

        /**
         * Open the multi-currency popover for an aggregated monetary field.
         *
         * @param {Event} ev
         * @param {any} value
         * @param {string} fieldName
         */
        openMultiCurrencyPopover(ev, value, fieldName) {
            if (!multiCurrencyPopover.isOpen) {
                multiCurrencyPopover.open(/** @type {HTMLElement} */ (ev.target), {
                    currencyIds: Array.from(self.getFieldCurrencies(fieldName)),
                    target: /** @type {HTMLElement} */ (ev.target),
                    value,
                });
            }
        },
    };

    return self;
}
