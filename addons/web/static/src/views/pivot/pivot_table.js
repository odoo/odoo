// @ts-check

/**
 * Pivot table layout helpers.
 *
 * Transforms the in-memory pivot data structures (group trees,
 * measurements) into row/column arrays suitable for rendering
 * an HTML table: header rows with col-group hierarchy and span
 * calculations, and body rows with cell values and indentation.
 *
 * @module pivot_table
 */

import { _t } from "@web/core/l10n/translation";

import { getLeafCounts } from "./pivot_group_tree";
import { getCellCurrency, getCellValue, getMeasuresRow } from "./pivot_measurements";

/**
 * Returns the list of header rows of the pivot table: the col group rows
 * (depending on the col groupbys), the measures row.
 *
 * @param {Object} data
 * @param {Object} metaData
 * @returns {Object[]}
 */
export function getTableHeaders(data, metaData) {
    const colGroupBys = metaData.fullColGroupBys;
    const height = colGroupBys.length + 1;
    const measureCount = metaData.activeMeasures.length;
    const leafCounts = getLeafCounts(data.colGroupTree);
    let headers = [];
    const measureColumns = [];

    // 1) generate col group rows (total row + one row for each col groupby)
    const colGroupRows = Array.from({ length: height }, () => []);
    // blank top left cell
    colGroupRows[0].push({
        height: height + 1,
        title: "",
        width: 1,
    });

    // col groupby cells with group values
    function generateTreeHeaders(tree) {
        const group = tree.root;
        const rowIndex = group.values.length;
        const row = colGroupRows[rowIndex];
        const groupId = [[], group.values];
        const isLeaf = !tree.directSubTrees.size;
        const leafCount = leafCounts[JSON.stringify(tree.root.values)];
        const cell = {
            groupId,
            height: isLeaf ? colGroupBys.length + 1 - rowIndex : 1,
            isLeaf,
            isFolded: isLeaf && colGroupBys.length > group.values.length,
            label:
                rowIndex === 0
                    ? undefined
                    : metaData.fields[colGroupBys[rowIndex - 1].split(":")[0]].string,
            title: group.labels.length ? group.labels.at(-1) : _t("Total"),
            width: leafCount * measureCount,
        };
        row.push(cell);
        if (isLeaf) {
            measureColumns.push(cell);
        }
        for (const subTree of tree.directSubTrees.values()) {
            generateTreeHeaders(subTree);
        }
    }

    generateTreeHeaders(data.colGroupTree);

    // blank top right cell for 'Total' group (if there is more than one leaf)
    if (leafCounts[JSON.stringify(data.colGroupTree.root.values)] > 1) {
        const groupId = [[], []];
        const totalTopRightCell = {
            groupId,
            height,
            title: "",
            width: measureCount,
        };
        colGroupRows[0].push(totalTopRightCell);
        measureColumns.push(totalTopRightCell);
    }
    headers = [...headers, ...colGroupRows];

    // 2) generate measures row
    const measuresRow = getMeasuresRow(measureColumns, metaData);
    headers.push(measuresRow);

    return headers;
}

/**
 * Returns the list of body rows of the pivot table for a given tree.
 *
 * @param {Object} tree
 * @param {Object[]} columns
 * @param {Object} data
 * @param {Object} metaData
 * @returns {Object[]}
 */
export function getTableRows(tree, columns, data, metaData) {
    let rows = [];
    const group = tree.root;
    const rowGroupId = [group.values, []];
    const title = group.labels.length ? group.labels.at(-1) : _t("Total");
    const indent = group.labels.length;
    const isLeaf = !tree.directSubTrees.size;
    const rowGroupBys = metaData.fullRowGroupBys;

    const subGroupMeasurements = columns.map((column) => {
        const colGroupId = column.groupId;
        const groupIntersectionId = [rowGroupId[0], colGroupId[1]];
        const measure = column.measure;

        const value = getCellValue(groupIntersectionId, measure, data);
        const currencyIds = getCellCurrency(groupIntersectionId, measure, data);

        return {
            groupId: groupIntersectionId,
            measure,
            value,
            currencyIds,
            isBold: !groupIntersectionId[0].length || !groupIntersectionId[1].length,
        };
    });

    rows.push({
        title,
        label:
            indent === 0
                ? undefined
                : metaData.fields[rowGroupBys[indent - 1].split(":")[0]].string,
        groupId: rowGroupId,
        indent,
        isLeaf,
        isFolded: isLeaf && rowGroupBys.length > group.values.length,
        subGroupMeasurements,
    });

    const subTreeKeys = tree.sortedKeys || [...tree.directSubTrees.keys()];
    for (const subTreeKey of subTreeKeys) {
        const subTree = tree.directSubTrees.get(subTreeKey);
        rows = [...rows, ...getTableRows(subTree, columns, data, metaData)];
    }

    return rows;
}
