// @ts-check

import { navigateTo } from "../actions/helpers";
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "./pivot_helpers";

/**
 * @param {import("@odoo/o-spreadsheet").CellPosition} position
 * @param {import("@spreadsheet").SpreadsheetChildEnv} env
 * @returns {Promise<void>}
 */
export const SEE_RECORDS_PIVOT = async (position, env) => {
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const pivot = env.model.getters.getPivot(pivotId);
    await pivot.load();
    const { model } = pivot.definition;
    const { actionXmlId } = env.model.getters.getPivotDefinition(pivotId);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position);
    const domain = pivot.getPivotCellDomain(argsDomain);
    const name = await pivot.getModelLabel();
    await navigateTo(
        env,
        actionXmlId,
        {
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            domain,
        },
        { viewType: "list" }
    );
};

/**
 * @param {import("@odoo/o-spreadsheet").CellPosition} position
 * @param {import("@spreadsheet").SpreadsheetChildEnv} env
 * @returns {boolean}
 */
export const SEE_RECORDS_PIVOT_VISIBLE = (position, env) => {
    const cell = env.model.getters.getCorrespondingFormulaCell(position);
    const evaluatedCell = env.model.getters.getEvaluatedCell(position);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position);
    return (
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        evaluatedCell.value !== "" &&
        argsDomain !== undefined &&
        cell &&
        cell.isFormula &&
        getNumberOfPivotFormulas(cell.compiledFormula.tokens) === 1
    );
};

/**
 * Check if the cell is a pivot formula and if there is a filter matching the
 * pivot domain args.
 * e.g. =PIVOT.VALUE("1", "measure", "country_id", 1) matches a filter on
 * country_id.
 *
 * @returns {boolean}
 */
export function SET_FILTER_MATCHING_CONDITION(position, env) {
    if (!SEE_RECORDS_PIVOT_VISIBLE(position, env)) {
        return false;
    }
    const cell = env.model.getters.getCorrespondingFormulaCell(position);

    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const domainArgs = env.model.getters.getPivotDomainArgsFromPosition(position);
    if (domainArgs === undefined) {
        return false;
    }
    const matchingFilters = env.model.getters.getFiltersMatchingPivotArgs(pivotId, domainArgs);
    const pivotFunction = getFirstPivotFunction(cell.compiledFormula.tokens).functionName;
    return (
        (pivotFunction === "PIVOT.VALUE" ||
            pivotFunction === "PIVOT.HEADER" ||
            pivotFunction === "PIVOT") &&
        matchingFilters.length > 0
    );
}

export function SET_FILTER_MATCHING(position, env) {
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const domainArgs = env.model.getters.getPivotDomainArgsFromPosition(position);
    const filters = env.model.getters.getFiltersMatchingPivotArgs(pivotId, domainArgs);
    env.model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
}
