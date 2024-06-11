/** @odoo-module */
import { getNumberOfPivotFormulas } from "./pivot_helpers";

export const SEE_RECORDS_PIVOT = async (position, env) => {
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const { model } = env.model.getters.getPivotDefinition(pivotId);
    const dataSource = await env.model.getters.getAsyncPivotDataSource(pivotId);

    const argsDomain = env.model.getters.getPivotDomainArgsFromPosition(position)?.domainArgs;
    const domain = dataSource.getPivotCellDomain(argsDomain);
    const name = await dataSource.getModelLabel();
    await env.services.action.doAction({
        type: "ir.actions.act_window",
        name,
        res_model: model,
        view_mode: "list",
        views: [
            [false, "list"],
            [false, "form"],
        ],
        target: "current",
        domain,
    });
};

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
};

/**
 * Check if the cell is a pivot formula and if there is a filter matching the
 * pivot domain args.
 * e.g. =ODOO.PIVOT("1", "measure", "country_id", 1) matches a filter on
 * country_id.
 *
 * @returns {boolean}
 */
export function SET_FILTER_MATCHING_CONDITION(position, env) {
    if (!SEE_RECORDS_PIVOT_VISIBLE(position, env)) {
        return false;
    }

    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const pivotInfo = env.model.getters.getPivotDomainArgsFromPosition(position);
    if (pivotInfo?.domainArgs === undefined) {
        return false;
    }
    const matchingFilters = env.model.getters.getFiltersMatchingPivotArgs(
        pivotId,
        pivotInfo?.domainArgs
    );
    return pivotInfo?.isHeader && matchingFilters.length > 0;
}

export function SET_FILTER_MATCHING(position, env) {
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const domainArgs = env.model.getters.getPivotDomainArgsFromPosition(position)?.domainArgs;
    const filters = env.model.getters.getFiltersMatchingPivotArgs(pivotId, domainArgs);
    env.model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
}
