// @ts-check

/** @module @web/views/pivot/pivot_measurements - Builds measure specs (fieldName:aggregator) and data comparison logic for the pivot model */

/**
 * Returns the list of measure specs associated with active measures.
 * A measure 'fieldName' becomes 'fieldName:aggregator'.
 *
 * @param {Object} config
 * @returns {string[]}
 */
export function getMeasureSpecs(config) {
    const { metaData } = config;
    return metaData.activeMeasures.reduce((acc, measure) => {
        if (measure === "__count") {
            acc.push(measure);
            return acc;
        }
        const field = metaData.fields[measure];
        if (field.type === "many2one") {
            field.aggregator = "count_distinct";
        }
        if (field.aggregator === undefined) {
            throw new Error(
                `No aggregate function has been provided for the measure '${measure}'`,
            );
        }
        acc.push(`${measure}:${field.aggregator}`);
        if (field.currency_field) {
            acc.push(`${field.currency_field}:array_agg_distinct`);
            acc.push(`${field.name}:sum_currency`);
        }
        return acc;
    }, []);
}

/**
 * Returns the group sanitized measure values for the active measures.
 *
 * @param {Object} group
 * @param {Object} config
 * @returns {Object}
 */
export function getMeasurements(group, config) {
    const { metaData } = config;
    return getMeasureSpecs(config).reduce((measurements, measureName) => {
        let measurement = group[measureName];
        const [fieldName, aggregator] = measureName.split(":");
        if (aggregator === "array_agg_distinct") {
            return measurements;
        }
        if (aggregator === "sum_currency") {
            const currencies =
                group[
                    `${metaData.fields[fieldName].currency_field}:array_agg_distinct`
                ];
            if (currencies.length === 1) {
                return measurements;
            }
        }
        if (
            metaData.measures[fieldName].type === "boolean" &&
            measurement instanceof Boolean
        ) {
            measurement = measurement ? 1 : 0;
        }
        measurements[fieldName] = measurement;
        return measurements;
    }, {});
}

/**
 * Returns the group sanitized currency id values for monetary measures.
 *
 * @param {Object} group
 * @param {Object} config
 * @returns {Object}
 */
export function getCurrencyIds(group, config) {
    const { metaData } = config;
    return getMeasureSpecs(config).reduce((currencyIds, measureName) => {
        const [fieldName, aggregator] = measureName.split(":");
        if (aggregator === "array_agg_distinct") {
            return currencyIds;
        }
        const measureField = metaData.measures[fieldName];
        if (measureField.type === "monetary" && measureField.currency_field) {
            currencyIds[fieldName] =
                group[`${measureField.currency_field}:array_agg_distinct`];
        }
        return currencyIds;
    }, {});
}

/**
 * @param {Array[]} groupId
 * @param {string} measure
 * @param {Object} data
 * @returns {number|undefined}
 */
export function getCellValue(groupId, measure, data) {
    const key = JSON.stringify(groupId);
    if (!data.measurements[key]) {
        return;
    }
    return data.measurements[key][measure];
}

/**
 * @param {Array[]} groupId
 * @param {string} measure
 * @param {Object} data
 * @returns {number|undefined}
 */
export function getCellCurrency(groupId, measure, data) {
    const key = JSON.stringify(groupId);
    if (!data.currencyIds[key]) {
        return;
    }
    return data.currencyIds[key][measure];
}

/**
 * Returns a description of the measures row of the pivot table.
 *
 * @param {Object[]} columns
 * @param {Object} metaData
 * @returns {Object[]}
 */
export function getMeasuresRow(columns, metaData) {
    const sortedColumn = metaData.sortedColumn || {};
    const measureRow = [];

    for (const column of columns) {
        for (const measureName of metaData.activeMeasures) {
            const measureCell = {
                groupId: column.groupId,
                height: 1,
                measure: measureName,
                title: metaData.measures[measureName].string,
                width: 1,
            };
            if (
                sortedColumn.measure === measureName &&
                JSON.stringify(sortedColumn.groupId) === JSON.stringify(column.groupId)
            ) {
                measureCell.order = sortedColumn.order;
            }
            measureRow.push(measureCell);
        }
    }

    return measureRow;
}
