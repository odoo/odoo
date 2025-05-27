/** @ts-check */

import { helpers } from "@odoo/o-spreadsheet";
import { globalFieldMatchingRegistry } from "@spreadsheet/global_filters/helpers";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

const { UuidGenerator } = helpers;

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").DateGlobalFilter} DateGlobalFilter
 * @typedef {import("@spreadsheet").RelationalGlobalFilter} RelationalGlobalFilter
 */

import { OdooUIPlugin } from "@spreadsheet/plugins";

export class GlobalFiltersUIPlugin extends OdooUIPlugin {
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "AUTO_MATCH_GLOBAL_FILTERS": {
                const matcher = globalFieldMatchingRegistry.get(cmd.dataSourceType);
                return !matcher.isValid(this.getters, cmd.dataSourceId)
                    ? CommandResult.DataSourceNotValid
                    : CommandResult.Success;
            }
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
            case "AUTO_MATCH_GLOBAL_FILTERS": {
                const matcher = globalFieldMatchingRegistry.get(cmd.dataSourceType);
                const dataSourceId = cmd.dataSourceId;
                const fieldNames = cmd.fieldNames;
                const fields = matcher.getFields(this.getters, dataSourceId);
                this.generateMissingGlobalFilters(fields, fieldNames);
                this.autoMatchFields(matcher, fields, cmd.dataSourceType, dataSourceId, fieldNames);
            }
        }
    }

    generateMissingGlobalFilters(fields, fieldNames) {
        const uuidGenerator = new UuidGenerator();
        for (const fieldName of fieldNames) {
            const coModel = fields[fieldName]?.relation;
            const matchingFilters = fieldNames.filter(
                (globalFilter) => globalFilter.modelName === coModel
            );
            if (matchingFilters.length === 0) {
                const filter = {
                    id: uuidGenerator.smallUuid(),
                    modelName: coModel,
                    type: "relation",
                    label: fields[fieldName]?.string,
                };
                this.dispatch("ADD_GLOBAL_FILTER", { filter });
            }
        }
    }

    autoMatchFields(dataSourceMatcher, fields, dataSourceType, dataSourceId, fieldNames) {
        const matcher = dataSourceMatcher;
        for (const filter of this.getters.getGlobalFilters()) {
            let matchingField;
            if (filter.modelName === matcher.getModel(this.getters, dataSourceId)) {
                matchingField = "id";
            } else {
                matchingField = fieldNames
                    .map((name) => fields[name])
                    .find((field) => field.searchable && field.relation === filter.modelName)?.name;
            }
            if (matchingField) {
                const existingMatching = {};
                for (const dataSourceId of matcher.getIds(this.getters)) {
                    existingMatching[dataSourceId] =
                        matcher.getFieldMatching(this.getters, dataSourceId, filter.id) ?? {};
                }
                existingMatching[dataSourceId] = {
                    chain: matchingField,
                    type: fields[matchingField]?.type,
                };
                this.dispatch("EDIT_GLOBAL_FILTER", {
                    filter,
                    [dataSourceType]: existingMatching,
                });
            }
        }
    }
}
