/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getFirstListFunction, getNumberOfListFormulas } from "./list_helpers";

const { astToFormula } = spreadsheet;

export const SEE_RECORD_LIST = async (cell, env) => {
    const { col, row, sheetId } = env.model.getters.getCellPosition(cell.id);
    if (!cell) {
        return;
    }
    const { args } = getFirstListFunction(cell.content);
    const evaluatedArgs = args
        .map(astToFormula)
        .map((arg) => env.model.getters.evaluateFormula(arg));
    const listId = env.model.getters.getListIdFromPosition(sheetId, col, row);
    const { model } = env.model.getters.getListDefinition(listId);
    const dataSource = await env.model.getters.getAsyncListDataSource(listId);
    const recordId = dataSource.getIdFromPosition(evaluatedArgs[1] - 1);
    if (!recordId) {
        return;
    }
    await env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: model,
        res_id: recordId,
        views: [[false, "form"]],
        view_mode: "form",
    });
};

export const SEE_RECORD_LIST_VISIBLE = (cell) => {
    return (
        cell &&
        cell.evaluated.value !== "" &&
        !cell.evaluated.error &&
        getNumberOfListFormulas(cell.content) === 1 &&
        getFirstListFunction(cell.content).functionName === "ODOO.LIST"
    );
};
