/** @odoo-module */
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "./pivot_helpers";

const { astToFormula } = spreadsheet;

export const SEE_RECORDS_PIVOT = async (cell, env) => {
    const { col, row, sheetId } = env.model.getters.getCellPosition(cell.id);
    const { args, functionName } = getFirstPivotFunction(cell.content);
    const evaluatedArgs = args
        .map(astToFormula)
        .map((arg) => env.model.getters.evaluateFormula(arg));
    const pivotId = env.model.getters.getPivotIdFromPosition(sheetId, col, row);
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

export const SEE_RECORDS_PIVOT_VISIBLE = (cell) => {
    return (
        cell &&
        cell.evaluated.value !== "" &&
        !cell.evaluated.error &&
        getNumberOfPivotFormulas(cell.content) === 1
    );
};
