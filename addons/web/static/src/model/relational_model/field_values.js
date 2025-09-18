// @ts-check

/** @module @web/model/relational_model/field_values - Server value parsing, aggregation constants, and default value helpers */

import { markup } from "@odoo/owl";
/** @import { Field } from "@web/search/search_model" */
import { Domain } from "@web/core/domain";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { unique } from "@web/core/utils/collections/arrays";
import { x2ManyCommands } from "@web/services/orm_service";

const granularityToInterval = {
    hour: { hours: 1 },
    day: { days: 1 },
    week: { days: 7 },
    month: { month: 1 },
    quarter: { month: 4 },
    year: { year: 1 },
};

export const AGGREGATABLE_FIELD_TYPES = ["float", "integer", "monetary"]; // types that can be aggregated in grouped views

/**
 * @protected
 * @param {Field} field
 * @param {any} value
 * @returns {any}
 */
export function parseServerValue(field, value) {
    switch (field.type) {
        case "char":
        case "text": {
            return value || "";
        }
        case "html": {
            return markup(value || "");
        }
        case "date": {
            return value ? deserializeDate(value) : false;
        }
        case "datetime": {
            return value ? deserializeDateTime(value) : false;
        }
        case "selection": {
            if (value === false) {
                // process selection: convert false to 0, if 0 is a valid key
                const hasKey0 = field.selection.find((option) => option[0] === 0);
                return hasKey0 ? 0 : value;
            }
            return value;
        }
        case "reference": {
            if (value === false) {
                return false;
            }
            return {
                resId: value.id.id,
                resModel: value.id.model,
                displayName: value.display_name,
            };
        }
        case "many2one_reference": {
            if (value === 0) {
                // unset many2one_reference fields' value is 0
                return false;
            }
            if (typeof value === "number") {
                // many2one_reference fetched without "fields" key in spec -> only returns the id
                return { resId: value };
            }
            return {
                resId: value.id,
                displayName: value.display_name,
            };
        }
        case "many2one": {
            if (Array.isArray(value)) {
                // Used for web_read_group, where the value is an array of [id, display_name]
                value = { id: value[0], display_name: value[1] };
            }
            return value;
        }
        case "properties": {
            return value
                ? value.map((property) => {
                      if (property.value !== undefined) {
                          property.value = parseServerValue(
                              property,
                              property.value ?? false,
                          );
                      }
                      if (property.default !== undefined) {
                          property.default = parseServerValue(
                              property,
                              property.default ?? false,
                          );
                      }
                      return property;
                  })
                : [];
        }
    }
    return value;
}

export function getAggregateSpecifications(fields) {
    const aggregatableFields = Object.values(fields)
        .filter(
            (field) =>
                field.aggregator && AGGREGATABLE_FIELD_TYPES.includes(field.type),
        )
        .map((field) => `${field.name}:${field.aggregator}`);
    const currencyFields = unique(
        Object.values(fields)
            .filter((field) => field.aggregator && field.currency_field)
            .map((field) => [
                `${field.currency_field}:array_agg_distinct`,
                `${field.name}:sum_currency`,
            ])
            .flat(),
    );
    return [...aggregatableFields, ...currencyFields];
}

/**
 * Extract useful information from a group data returned by a call to webReadGroup.
 *
 * @param {Object} groupData
 * @param {string[]} groupBy
 * @param {Object} fields
 * @returns {Object}
 */
export function extractInfoFromGroupData(groupData, groupBy, fields, domain) {
    const info = {};
    const groupByField = fields[groupBy[0].split(":")[0]];
    info.count = groupData.__count;
    info.length = info.count; // Alias: DynamicRecordList._updateCount reads .length
    info.domain = Domain.and([domain, groupData.__extra_domain]).toList();
    info.rawValue = groupData[groupBy[0]];
    info.value = getValueFromGroupData(groupByField, info.rawValue);
    if (["date", "datetime"].includes(groupByField.type) && info.value) {
        const granularity = groupBy[0].split(":")[1];
        info.range = {
            from: info.value,
            to: info.value.plus(granularityToInterval[granularity]),
        };
    }
    info.displayName = getDisplayNameFromGroupData(groupByField, info.rawValue);
    info.serverValue = getGroupServerValue(groupByField, info.value);
    info.aggregates = getAggregatesFromGroupData(groupData, fields);
    info.values = groupData.__values; // Extra data of the relational groupby field record
    return info;
}

/**
 * @param {Object} groupData
 * @returns {Object}
 */
function getAggregatesFromGroupData(groupData, fields) {
    const aggregates = {};
    for (const keyAggregate of getAggregateSpecifications(fields)) {
        if (keyAggregate in groupData) {
            const [fieldName, aggregate] = keyAggregate.split(":");
            if (aggregate === "sum_currency") {
                const currencies =
                    groupData[`${fields[fieldName].currency_field}:array_agg_distinct`];
                if (currencies.length === 1) {
                    continue;
                }
            }
            aggregates[fieldName] = groupData[keyAggregate];
        }
    }
    return aggregates;
}

/**
 * @param {any} field
 * @param {any} rawValue
 * @returns {string}
 */
function getDisplayNameFromGroupData(field, rawValue) {
    switch (field.type) {
        case "selection": {
            return Object.fromEntries(field.selection)[rawValue];
        }
        case "boolean": {
            return rawValue ? _t("Yes") : _t("No");
        }
        case "integer": {
            return rawValue ? String(rawValue) : "0";
        }
        case "many2one":
        case "many2many":
        case "date":
        case "datetime":
        case "tags": {
            return (rawValue && rawValue[1]) || field.falsy_value_label || _t("None");
        }
    }
    return rawValue ? String(rawValue) : field.falsy_value_label || _t("None");
}

/**
 * @param {any} field
 * @param {any} value
 * @returns {any}
 */
export function getGroupServerValue(field, value) {
    switch (field.type) {
        case "many2many": {
            return value ? [value] : false;
        }
        case "datetime": {
            return value ? serializeDateTime(value) : false;
        }
        case "date": {
            return value ? serializeDate(value) : false;
        }
        default: {
            return value ?? false;
        }
    }
}

/**
 * @param {Field} field
 * @param {any} rawValue
 * @returns {any}
 */
function getValueFromGroupData(field, rawValue) {
    if (["date", "datetime"].includes(field.type)) {
        if (!rawValue) {
            return false;
        }
        return parseServerValue(field, rawValue[0]);
    }
    const value = parseServerValue(field, rawValue);
    if (field.type === "many2one") {
        return value?.id;
    }
    if (field.type === "many2many") {
        return value ? value[0] : false;
    }
    if (field.type === "tags") {
        return value ? value[0] : false;
    }
    return value;
}

/**
 * Onchanges sometimes return update commands for records we don't know (e.g. if
 * they are on a page we haven't loaded yet). We may actually never load them.
 * When this happens, we must still be able to send back those commands to the
 * server when saving. However, we can't send the commands exactly as we received
 * them, since the values they contain have been "unity read". The purpose of this
 * function is to transform field values from the unity format to the format
 * expected by the server for a write.
 * For instance, for a many2one: { id: 3, display_name: "Marc" } => 3.
 * @param {Record<string, unknown>} values
 * @param {Record<string, object>} fields
 * @param {Record<string, object>} activeFields
 * @param {{ withReadonly?: boolean, context?: Record<string, unknown> }} [options]
 */
export function fromUnityToServerValues(
    values,
    fields,
    activeFields,
    { withReadonly, context } = {},
) {
    const { CREATE, UPDATE } = x2ManyCommands;
    const serverValues = {};
    for (const fieldName in values) {
        /** @type {any} */
        let value = values[fieldName];
        const field = fields[fieldName];
        const activeField = activeFields[fieldName];
        if (!withReadonly) {
            if (field.readonly) {
                continue;
            }
            try {
                if (evaluateExpr(activeField.readonly, context)) {
                    continue;
                }
            } catch {
                // if the readonly expression depends on other fields, we can't evaluate it as we
                // didn't read the record, so we simply ignore it
            }
        }
        switch (fields[fieldName].type) {
            case "one2many":
            case "many2many":
                value = value.map((c) => {
                    if (c[0] === CREATE || c[0] === UPDATE) {
                        const _fields = activeField.related.fields;
                        const _activeFields = activeField.related.activeFields;
                        return [
                            c[0],
                            c[1],
                            fromUnityToServerValues(c[2], _fields, _activeFields, {
                                withReadonly,
                            }),
                        ];
                    }
                    return [c[0], c[1]];
                });
                break;
            case "many2one":
                value = value ? value.id : false;
                break;
            // case "reference":
            //     // TODO
            //     break;
        }
        serverValues[fieldName] = value;
    }
    return serverValues;
}
