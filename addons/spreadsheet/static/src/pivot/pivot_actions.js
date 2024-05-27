// @ts-check

import { navigateTo } from "../actions/helpers";
<<<<<<< HEAD
import { helpers } from "@odoo/o-spreadsheet";
const { getFirstPivotFunction, getNumberOfPivotFunctions } = helpers;
||||||| parent of d7fb5e0273d6 (temp)
import {
  getFirstPivotFunction,
  getNumberOfPivotFormulas,
} from "./pivot_helpers";
=======
import { getNumberOfPivotFormulas } from "./pivot_helpers";
>>>>>>> d7fb5e0273d6 (temp)

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
<<<<<<< HEAD
    const { actionXmlId } = env.model.getters.getPivotCoreDefinition(pivotId);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position);
||||||| parent of d7fb5e0273d6 (temp)
    const { actionXmlId } = env.model.getters.getPivotDefinition(pivotId);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position);
=======
    const { actionXmlId } = env.model.getters.getPivotDefinition(pivotId);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position)?.domainArgs;
>>>>>>> d7fb5e0273d6 (temp)
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
 * @param {import("@spreadsheet").OdooGetters} getters
 * @returns {boolean}
 */
<<<<<<< HEAD
export const SEE_RECORDS_PIVOT_VISIBLE = (position, getters) => {
    const cell = getters.getCorrespondingFormulaCell(position);
    const evaluatedCell = getters.getEvaluatedCell(position);
    const argsDomain = getters.getPivotDomainArgsFromPosition(position);
||||||| parent of d7fb5e0273d6 (temp)
export const SEE_RECORDS_PIVOT_VISIBLE = (position, env) => {
    const cell = env.model.getters.getCorrespondingFormulaCell(position);
    const evaluatedCell = env.model.getters.getEvaluatedCell(position);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position);
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    if (!env.model.getters.isExistingPivot(pivotId)) {
        return false;
    }
    const dataSource = env.model.getters.getPivot(pivotId);
    const loadingError = dataSource.assertIsValid({ throwOnError: false })
=======
export const SEE_RECORDS_PIVOT_VISIBLE = (position, env) => {
    const cell = env.model.getters.getCorrespondingFormulaCell(position);
    const evaluatedCell = env.model.getters.getEvaluatedCell(position);
    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position)?.domainArgs;
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    if (!env.model.getters.isExistingPivot(pivotId)) {
        return false;
    }
    const dataSource = env.model.getters.getPivot(pivotId);
    const loadingError = dataSource.assertIsValid({ throwOnError: false })
>>>>>>> d7fb5e0273d6 (temp)
    return (
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        evaluatedCell.value !== "" &&
        argsDomain !== undefined &&
        cell &&
        cell.isFormula &&
        getNumberOfPivotFunctions(cell.compiledFormula.tokens) === 1
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
export function SET_FILTER_MATCHING_CONDITION(position, getters) {
    if (!SEE_RECORDS_PIVOT_VISIBLE(position, getters)) {
        return false;
    }
<<<<<<< HEAD
    const cell = getters.getCorrespondingFormulaCell(position);
||||||| parent of d7fb5e0273d6 (temp)
    const cell = env.model.getters.getCorrespondingFormulaCell(position);
=======
>>>>>>> d7fb5e0273d6 (temp)

<<<<<<< HEAD
    const pivotId = getters.getPivotIdFromPosition(position);
    const domainArgs = getters.getPivotDomainArgsFromPosition(position);
    if (domainArgs === undefined) {
||||||| parent of d7fb5e0273d6 (temp)
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const domainArgs = env.model.getters.getPivotDomainArgsFromPosition(position);
    if (domainArgs === undefined) {
=======
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const pivotInfo = env.model.getters.getPivotDomainArgsFromPosition(position);
    if (pivotInfo?.domainArgs === undefined) {
>>>>>>> d7fb5e0273d6 (temp)
        return false;
    }
<<<<<<< HEAD
    const matchingFilters = getters.getFiltersMatchingPivotArgs(pivotId, domainArgs);
    const pivotFunction = getFirstPivotFunction(cell.compiledFormula.tokens).functionName;
    return (
        (pivotFunction === "PIVOT.VALUE" ||
            pivotFunction === "PIVOT.HEADER" ||
            pivotFunction === "PIVOT") &&
        matchingFilters.length > 0
||||||| parent of d7fb5e0273d6 (temp)
    const matchingFilters = env.model.getters.getFiltersMatchingPivotArgs(pivotId, domainArgs);
    const pivotFunction = getFirstPivotFunction(cell.compiledFormula.tokens).functionName;
    return (
        (pivotFunction === "ODOO.PIVOT" ||
            pivotFunction === "ODOO.PIVOT.HEADER" ||
            pivotFunction === "ODOO.PIVOT.TABLE") &&
        matchingFilters.length > 0
=======
    const matchingFilters = env.model.getters.getFiltersMatchingPivotArgs(
        pivotId,
        pivotInfo?.domainArgs
>>>>>>> d7fb5e0273d6 (temp)
    );
    return pivotInfo?.isHeader && matchingFilters.length > 0;
}

export function SET_FILTER_MATCHING(position, env) {
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const domainArgs = env.model.getters.getPivotDomainArgsFromPosition(position)?.domainArgs;
    const filters = env.model.getters.getFiltersMatchingPivotArgs(pivotId, domainArgs);
    env.model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
}
