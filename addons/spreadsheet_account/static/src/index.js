/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import AccountingPlugin from "./plugins/accounting_plugin";
import { getFirstAccountFunction, getNumberOfAccountFormulas } from "./utils";
import { parseAccountingDate } from "./accounting_functions";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";

const { cellMenuRegistry, uiPluginRegistry } = spreadsheet.registries;
const { astToFormula } = spreadsheet;
const { toString, toBoolean } = spreadsheet.helpers;

uiPluginRegistry.add("odooAccountingAggregates", AccountingPlugin);

cellMenuRegistry.add("move_lines_see_records", {
    name: _lt("See records"),
    sequence: 176,
    async action(env) {
        const cell = env.model.getters.getActiveCell();
        const { args } = getFirstAccountFunction(cell.content);
        let [code, date_range, offset, companyId, includeUnposted] = args
            .map(astToFormula)
            .map((arg) => env.model.getters.evaluateFormula(arg));
        code = toString(code);
        const dateRange = parseAccountingDate(date_range);
        dateRange.year += offset || 0;
        companyId = companyId || null;
        includeUnposted = toBoolean(includeUnposted);

        const action = await env.services.orm.call(
            "account.account",
            "spreadsheet_move_line_action",
            [camelToSnakeObject({ dateRange, companyId, code, includeUnposted })]
        );
        await env.services.action.doAction(action);
    },
    isVisible: (env) => {
        const cell = env.model.getters.getActiveCell();
        return (
            cell && !cell.evaluated.error &&
            cell.evaluated.value !== "" && getNumberOfAccountFormulas(cell.content) === 1
        );
    },
});
