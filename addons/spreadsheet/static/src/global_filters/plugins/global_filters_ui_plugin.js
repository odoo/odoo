/** @ts-check */
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

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
}
