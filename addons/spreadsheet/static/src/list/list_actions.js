/** @odoo-module */

import { astToFormula } from "@odoo/o-spreadsheet";
import { getFirstListFunction, getNumberOfListFormulas } from "./list_helpers";

export const SEE_RECORD_LIST = async (position, env) => {
    const cell = env.model.getters.getCell(position);
    const sheetId = position.sheetId;
    if (!cell) {
        return;
    }
    const { args } = getFirstListFunction(cell.content);
    const evaluatedArgs = args
        .map(astToFormula)
        .map((arg) => env.model.getters.evaluateFormula(sheetId, arg));
    const listId = env.model.getters.getListIdFromPosition(position);
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

export const SEE_RECORD_LIST_VISIBLE = (position, env) => {
    const evaluatedCell = env.model.getters.getEvaluatedCell(position);
    const cell = env.model.getters.getCell(position);
    return (
        evaluatedCell.type !== "empty" &&
        evaluatedCell.type !== "error" &&
        cell &&
        getNumberOfListFormulas(cell.content) === 1 &&
        getFirstListFunction(cell.content).functionName === "ODOO.LIST"
    );
};
