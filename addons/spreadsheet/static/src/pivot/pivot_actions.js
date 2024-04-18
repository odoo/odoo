/** @odoo-module */
import { astToFormula } from "@odoo/o-spreadsheet";
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "./pivot_helpers";

export const SEE_RECORDS_PIVOT = async (position, env) => {
    const cell = env.model.getters.getCell(position);
    const sheetId = position.sheetId;
    if (!cell) {
        return;
    }
    const { args, functionName } = getFirstPivotFunction(cell.content);
    const evaluatedArgs = args
        .map(astToFormula)
        .map((arg) => env.model.getters.evaluateFormula(sheetId, arg));
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    const { model } = env.model.getters.getPivotDefinition(pivotId);
    const dataSource = await env.model.getters.getAsyncPivotDataSource(pivotId);
    const slice = functionName === "ODOO.PIVOT.HEADER" ? 1 : 2;
    let argsDomain = evaluatedArgs.slice(slice);
    if (argsDomain[argsDomain.length - 2] === "measure") {
        // We have to remove the measure from the domain
        argsDomain = argsDomain.slice(0, argsDomain.length - 2);
    }
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
    const evaluatedCell = env.model.getters.getEvaluatedCell(position);
    const cell = env.model.getters.getCell(position);
    const pivotId = env.model.getters.getPivotIdFromPosition(position);
    if (!env.model.getters.isExistingPivot(pivotId)) {
        return false;
    }
    const dataSource = env.model.getters.getPivotDataSource(pivotId);
    return (
        dataSource.isReady() &&
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        cell &&
        getNumberOfPivotFormulas(cell.content) === 1
    );
};
