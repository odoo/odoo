/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { AccountingPlugin } from "./plugins/accounting_plugin";
import { getFirstAccountFunction, getNumberOfAccountFormulas } from "./utils";
import { parseAccountingDate } from "./accounting_functions";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";

const { cellMenuRegistry, featurePluginRegistry } = spreadsheet.registries;
const { astToFormula } = spreadsheet;
const { toString, toBoolean } = spreadsheet.helpers;

featurePluginRegistry.add("odooAccountingAggregates", AccountingPlugin);

cellMenuRegistry.add("move_lines_see_records", {
    name: _t("See records"),
    sequence: 176,
    async execute(env) {
        const position = env.model.getters.getActivePosition();
        const sheetId = position.sheetId;
        const cell = env.model.getters.getCell(position);
        const { args } = getFirstAccountFunction(cell.compiledFormula.tokens);
        let [codes, date_range, offset, companyId, includeUnposted] = args
            .map(astToFormula)
            .map((arg) => env.model.getters.evaluateFormulaResult(sheetId, arg));
        codes = toString(codes?.value).split(",");
        const locale = env.model.getters.getLocale();
        const dateRange = parseAccountingDate(date_range, locale);
        offset = parseInt(offset?.value) || 0;
        dateRange.year += offset || 0;
        companyId = parseInt(companyId?.value) || null;
        try {
            includeUnposted = toBoolean(includeUnposted.value);
        } catch {
            includeUnposted = false;
        }

        const action = await env.services.orm.call(
            "account.account",
            "spreadsheet_move_line_action",
            [camelToSnakeObject({ dateRange, companyId, codes, includeUnposted })]
        );
        await env.services.action.doAction(action);
    },
    isVisible: (env) => {
        const position = env.model.getters.getActivePosition();
        const evaluatedCell = env.model.getters.getEvaluatedCell(position);
        const cell = env.model.getters.getCell(position);
        return (
            !evaluatedCell.error &&
            evaluatedCell.value !== "" &&
            cell &&
            cell.isFormula &&
            getNumberOfAccountFormulas(cell.compiledFormula.tokens) === 1
        );
    },
    icon: "o-spreadsheet-Icon.SEE_RECORDS",
});
