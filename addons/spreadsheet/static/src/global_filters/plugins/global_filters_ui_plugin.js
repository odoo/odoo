/** @ts-check */
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { getItemId } from "../../helpers/model";
import { helpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { UuidGenerator, createEmptyExcelSheet, createEmptySheet, toXC } = helpers;

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").DateGlobalFilter} DateGlobalFilter
 * @typedef {import("@spreadsheet").RelationalGlobalFilter} RelationalGlobalFilter
 */

import { OdooUIPlugin } from "@spreadsheet/plugins";
import {
    globalFieldMatchingRegistry,
    checkFilterAndValue,
} from "@spreadsheet/global_filters/helpers";

export class GlobalFiltersUIPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ (["exportSheetWithActiveFilters"]);

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "SET_MANY_GLOBAL_FILTER_VALUE":
                for (const { filterId, value } of cmd.filters) {
                    const result = checkFilterAndValue(this.getters, filterId, value);
                    if (result !== CommandResult.Success) {
                        return result;
                    }
                }
                return CommandResult.Success;
        }
        return CommandResult.Success;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {import("@spreadsheet").AllCommand} cmd
     */
    handle(cmd) {
        switch (cmd.type) {
            case "SET_MANY_GLOBAL_FILTER_VALUE":
                for (const filter of cmd.filters) {
                    this.dispatch("SET_GLOBAL_FILTER_VALUE", {
                        id: filter.filterId,
                        value: filter.value,
                    });
                }
                break;
            case "SET_DATASOURCE_FIELD_MATCHING": {
                const matcher = globalFieldMatchingRegistry.get(cmd.dataSourceType);
                /**
                 * cmd.fieldMatchings looks like { [filterId]: { chain, type } }
                 */
                for (const filterId in cmd.fieldMatchings) {
                    const filterFieldMatching = {};
                    for (const dataSourceId of matcher.getIds(this.getters)) {
                        if (dataSourceId === cmd.dataSourceId) {
                            filterFieldMatching[dataSourceId] = cmd.fieldMatchings[filterId];
                        } else {
                            filterFieldMatching[dataSourceId] =
                                matcher.getFieldMatching(this.getters, dataSourceId, filterId) ||
                                {};
                        }
                    }
                    this.dispatch("EDIT_GLOBAL_FILTER", {
                        filter: this.getters.getGlobalFilter(filterId),
                        [cmd.dataSourceType]: filterFieldMatching,
                    });
                }
            }
        }
    }

    /**
     * Adds all active filters (and their values) at the time of export in a dedicated sheet
     *
     * @param {Object} data
     */
    exportForExcel(data) {
        if (this.getters.getGlobalFilters().length === 0) {
            return;
        }
        this.exportSheetWithActiveFilters(data);
        data.sheets[data.sheets.length - 1] = {
            ...createEmptyExcelSheet(UuidGenerator.smallUuid(), _t("Active Filters")),
            ...data.sheets.at(-1),
        };
    }

    exportSheetWithActiveFilters(data) {
        if (this.getters.getGlobalFilters().length === 0) {
            return;
        }

        const cells = {
            A1: "Filter",
            B1: "Value",
        };
        const formats = {};
        let numberOfCols = 2; // at least 2 cols (filter title and filter value)
        let filterRowIndex = 1; // first row is the column titles
        for (const filter of this.getters.getGlobalFilters()) {
            cells[`A${filterRowIndex + 1}`] = filter.label;
            const result = this.getters.getFilterDisplayValue(filter.label);
            for (const colIndex in result) {
                numberOfCols = Math.max(numberOfCols, Number(colIndex) + 2);
                for (const rowIndex in result[colIndex]) {
                    const cell = result[colIndex][rowIndex];
                    if (cell.value === undefined) {
                        continue;
                    }
                    const xc = toXC(Number(colIndex) + 1, Number(rowIndex) + filterRowIndex);
                    cells[xc] = cell.value.toString();
                    if (cell.format) {
                        const formatId = getItemId(cell.format, data.formats);
                        formats[xc] = formatId;
                    }
                }
            }
            filterRowIndex += result[0].length;
        }
        const styleId = getItemId({ bold: true }, data.styles);

        const sheet = {
            ...createEmptySheet(UuidGenerator.smallUuid(), _t("Active Filters")),
            cells,
            formats,
            styles: {
                A1: styleId,
                B1: styleId,
            },
            colNumber: numberOfCols,
            rowNumber: filterRowIndex,
        };
        data.sheets.push(sheet);
    }
}
