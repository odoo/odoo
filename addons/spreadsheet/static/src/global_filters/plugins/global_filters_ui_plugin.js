/** @ts-check */

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").DateGlobalFilter} DateGlobalFilter
 * @typedef {import("@spreadsheet").RelationalGlobalFilter} RelationalGlobalFilter
 */

import { OdooUIPlugin } from "@spreadsheet/plugins";
import { globalFieldMatchingRegistry } from "../helpers";

export class GlobalFiltersUIPlugin extends OdooUIPlugin {
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
