import { Domain } from "@web/core/domain";
import { NO_RECORD_AT_THIS_POSITION } from "../pivot_model";
import { OdooCoreViewPlugin } from "@spreadsheet/plugins";

/**
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@odoo/o-spreadsheet").Token} Token
 * @typedef {import("@odoo/o-spreadsheet").PivotDomain} PivotDomain
 */

/**
 * Convert pivot period to the related filter value
 *
 * @param {string} value
 * @returns {object}
 */
function pivotPeriodToFilterValue(timeRange, value) {
    // reuse the same logic as in `parseAccountingDate`?
    if (typeof value === "number") {
        value = value.toString(10);
    }
    if (
        value === "false" || // the value "false" is the default value when there is no data for a group header
        typeof value !== "string"
    ) {
        // anything else then a string at this point is incorrect, so no filtering
        return undefined;
    }

    const year = Number.parseInt(value.split("/").at(-1), 10);
    if (isNaN(year)) {
        return undefined;
    }
    switch (timeRange) {
        case "year":
            return {
                type: "year",
                year,
            };
        case "month": {
            const month = value.includes("/") ? Number.parseInt(value.split("/")[0]) : -1;
            if (month <= 0 || month > 12) {
                return { type: "year", year };
            }
            return {
                type: "month",
                month,
                year,
            };
        }
        case "quarter": {
            const quarter = value.includes("/") ? Number.parseInt(value.split("/")[0]) : -1;
            if (quarter <= 0 || quarter > 4) {
                return { type: "year", year };
            }
            return {
                type: "quarter",
                quarter,
                year,
            };
        }
    }
}

export class PivotCoreViewGlobalFilterPlugin extends OdooCoreViewPlugin {
    static getters = /** @type {const} */ ([
        "getPivotComputedDomain",
        "getFiltersMatchingPivotArgs",
    ]);
    constructor(config) {
        super(config);
    }

    beforeHandle(cmd) {
        switch (cmd.type) {
            case "START":
                // make sure the domains are correctly set before
                // any evaluation
                this._addDomains();
                break;
        }
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
            case "REMOVE_GLOBAL_FILTER":
            case "SET_GLOBAL_FILTER_VALUE":
                this._addDomains();
                break;
            case "UPDATE_PIVOT":
            case "UPDATE_ODOO_PIVOT_DOMAIN":
                this._addDomain(cmd.pivotId);
                break;
            case "DUPLICATE_PIVOT":
                this._addDomain(cmd.newPivotId);
                break;
            case "UNDO":
            case "REDO": {
                if (
                    cmd.commands.find((command) =>
                        [
                            "ADD_GLOBAL_FILTER",
                            "EDIT_GLOBAL_FILTER",
                            "REMOVE_GLOBAL_FILTER",
                            "UPDATE_ODOO_PIVOT_DOMAIN",
                            "UPDATE_PIVOT",
                        ].includes(command.type)
                    )
                ) {
                    this._addDomains();
                }
                break;
            }
        }
    }

    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the computed domain of a pivot
     * CLEAN ME not used outside of tests
     * @param {string} pivotId Id of the pivot
     * @returns {Array}
     */
    getPivotComputedDomain(pivotId) {
        return this.getters.getPivot(pivotId).getDomainWithGlobalFilters();
    }

    /**
     * Get the filter impacted by a pivot
     * @param {string} pivotId Id of the pivot
     * @param {PivotDomain} PivotDomain
     */
    getFiltersMatchingPivotArgs(pivotId, PivotDomain) {
        const lastNode = PivotDomain.at(-1);
        if (!lastNode || lastNode.field === "measure") {
            return [];
        }
        const filters = this.getters.getGlobalFilters();
        const matchingFilters = [];

        for (const filter of filters) {
            const dataSource = this.getters.getPivot(pivotId);
            const { type } = this.getters.getPivotCoreDefinition(pivotId);
            if (type !== "ODOO") {
                continue;
            }
            const { field, granularity: time } = dataSource.parseGroupField(lastNode.field);
            const pivotFieldMatching = this.getters.getPivotFieldMatching(pivotId, filter.id);
            if (pivotFieldMatching && pivotFieldMatching.chain === field.name) {
                let value = dataSource.getLastPivotGroupValue(PivotDomain.slice(-1));
                if (value === NO_RECORD_AT_THIS_POSITION) {
                    continue;
                }
                let transformedValue;
                const currentValue = this.getters.getGlobalFilterValue(filter.id);
                switch (filter.type) {
                    case "date":
                        if (time) {
                            if (value === "false") {
                                transformedValue = undefined;
                            } else {
                                transformedValue = pivotPeriodToFilterValue(time, value);
                                if (
                                    JSON.stringify(transformedValue) ===
                                    JSON.stringify(currentValue)
                                ) {
                                    transformedValue = undefined;
                                }
                            }
                        } else {
                            continue;
                        }
                        break;
                    case "relation":
                        if (typeof value == "string") {
                            value = Number(value);
                            if (Number.isNaN(value)) {
                                break;
                            }
                        }
                        // A group by value of "none"
                        if (value === false) {
                            break;
                        }
                        if (JSON.stringify(currentValue) !== `[${value}]`) {
                            transformedValue = [value];
                        }
                        break;
                    case "text":
                        if (currentValue !== value) {
                            transformedValue = [value];
                        }
                        break;
                }
                matchingFilters.push({ filterId: filter.id, value: transformedValue });
            }
        }
        return matchingFilters;
    }

    // ---------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------

    /**
     * Add an additional domain to a pivot
     *
     * @private
     *
     * @param {string} pivotId pivot id
     */
    _addDomain(pivotId) {
        if (this.getters.getPivotCoreDefinition(pivotId).type !== "ODOO") {
            return;
        }
        const domainList = [];
        for (const [filterId, fieldMatch] of Object.entries(
            this.getters.getPivotFieldMatch(pivotId)
        )) {
            domainList.push(this.getters.getGlobalFilterDomain(filterId, fieldMatch));
        }
        const domain = Domain.combine(domainList, "AND").toString();
        this.getters.getPivot(pivotId).addGlobalFilterDomain(domain);
    }

    /**
     * Add an additional domain to all pivots
     *
     * @private
     *
     */
    _addDomains() {
        for (const pivotId of this.getters
            .getPivotIds()
            .filter((pivotId) => this.getters.getPivot(pivotId).type === "ODOO")) {
            this._addDomain(pivotId);
        }
    }
}
