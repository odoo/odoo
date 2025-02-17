// @ts-check

import { navigateTo } from "../actions/helpers";
import { helpers } from "@odoo/o-spreadsheet";
const { getNumberOfPivotFunctions } = helpers;

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
    const { actionXmlId, context } = env.model.getters.getPivotCoreDefinition(pivotId);
    const pivotCell = env.model.getters.getPivotCellFromPosition(position);
    const domain = pivot.getPivotCellDomain(pivotCell.domain);
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
            context,
        },
        { viewType: "list" }
    );
};

<<<<<<< saas-17.4
/**
 * @param {import("@odoo/o-spreadsheet").CellPosition} position
 * @param {import("@spreadsheet").OdooGetters} getters
 * @returns {boolean}
 */
export const SEE_RECORDS_PIVOT_VISIBLE = (position, getters) => {
    const cell = getters.getCorrespondingFormulaCell(position);
    const evaluatedCell = getters.getEvaluatedCell(position);
    const pivotId = getters.getPivotIdFromPosition(position);
    const pivotCell = getters.getPivotCellFromPosition(position);
    return (
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        evaluatedCell.value !== "" &&
        pivotCell.type !== "EMPTY" &&
        cell &&
        cell.isFormula &&
        getNumberOfPivotFunctions(cell.compiledFormula.tokens) === 1 &&
        getters.getPivotCoreDefinition(pivotId).type === "ODOO"
    );
||||||| 36fcb71454b3c1ad23c71b4e0a0424195b121883
export const SEE_RECORDS_PIVOT_VISIBLE = (position, env) => {
    const cell = env.model.getters.getCorrespondingFormulaCell(position);
    const evaluatedCell = env.model.getters.getEvaluatedCell(position);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position)?.domainArgs;
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    if (!env.model.getters.isExistingPivot(pivotId)) {
        return false;
    }
    const dataSource = env.model.getters.getPivotDataSource(pivotId);
    return (
        dataSource.isReady() &&
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        argsDomain !== undefined &&
        cell &&
        cell.isFormula &&
        getNumberOfPivotFormulas(cell.compiledFormula.tokens) === 1
    );
=======
export const SEE_RECORDS_PIVOT_VISIBLE = (position, env) => {
    const cell = env.model.getters.getCorrespondingFormulaCell(position);
    const evaluatedCell = env.model.getters.getEvaluatedCell(position);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position)?.domainArgs;
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    if (!env.model.getters.isExistingPivot(pivotId)) {
        return false;
    }
    const dataSource = env.model.getters.getPivotDataSource(pivotId);
    try {
        // parse the domain (field, value) to ensure they are of the correct type
        dataSource.getPivotCellDomain(argsDomain);
        return (
            dataSource.isReady() &&
            evaluatedCell.type !== "empty" &&
            evaluatedCell.type !== "error" &&
            argsDomain !== undefined &&
            cell &&
            cell.isFormula &&
            getNumberOfPivotFormulas(cell.compiledFormula.tokens) === 1
        );
        // eslint-disable-next-line no-unused-vars
    } catch (e) {
        // if the arguments of the domain are not correct, don't let the user click on it.
        return false;
    }
>>>>>>> 9ae58a7afb17e979990e6a06b879ff898c61ea4e
};

/**
 * Check if the cell is a pivot formula and if there is a filter matching the
 * pivot domain args.
 * e.g. =PIVOT.VALUE("1", "measure", "country_id", 1) matches a filter on
 * country_id.
 *
 * @returns {boolean}
 */
export function SET_FILTER_MATCHING_CONDITION(position, getters) {
    if (!SEE_RECORDS_PIVOT_VISIBLE(position, getters)) {
        return false;
    }

    const pivotId = getters.getPivotIdFromPosition(position);
    const pivotCell = getters.getPivotCellFromPosition(position);
    if (pivotCell.type === "EMPTY") {
        return false;
    }
    const matchingFilters = getters.getFiltersMatchingPivotArgs(pivotId, pivotCell.domain);
    return matchingFilters.length > 0 && pivotCell.type === "HEADER";
}

export function SET_FILTER_MATCHING(position, env) {
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const domain = env.model.getters.getPivotCellFromPosition(position).domain;
    const filters = env.model.getters.getFiltersMatchingPivotArgs(pivotId, domain);
    env.model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
}
