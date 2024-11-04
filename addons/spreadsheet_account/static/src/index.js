/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { AccountingPlugin } from "./plugins/accounting_plugin";
import { getFirstAccountFunction, getNumberOfAccountFormulas } from "./utils";
import { parseAccountingDate } from "./accounting_functions";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";

const { cellMenuRegistry, featurePluginRegistry } = spreadsheet.registries;
const { astToFormula } = spreadsheet;
const { isEvaluationError, toString, toBoolean } = spreadsheet.helpers;

featurePluginRegistry.add("odooAccountingAggregates", AccountingPlugin);

cellMenuRegistry.add("move_lines_see_records", {
    name: _t("See records"),
    sequence: 176,
    async execute(env) {
        const position = env.model.getters.getActivePosition();
        const sheetId = position.sheetId;
        const cell = env.model.getters.getCell(position);
        const { args } = getFirstAccountFunction(cell.compiledFormula.tokens);
        let codes, partner_ids = "";
        let date_range, offset, companyId, includeUnposted = false;
        const parsed_args = args.map(astToFormula).map(
            (arg) => env.model.getters.evaluateFormulaResult(sheetId, arg)
        );
        if ( cell.content.startsWith("=ODOO.PARTNER.BALANCE") ) {
            [partner_ids, codes, date_range, offset, companyId, includeUnposted] = parsed_args;
        } else {
            [codes, date_range, offset, companyId, includeUnposted] = parsed_args;
        }
        try {
            codes = toString(codes?.value).split(",");
        } catch {
            codes = [];
        }
        const locale = env.model.getters.getLocale();
        if ( 
            ( cell.content.startsWith("=ODOO.PARTNER.BALANCE")
              || cell.content.startsWith("=ODOO.RESIDUAL")
            ) && !date_range?.value
        ) {
            date_range = { value: new Date().getFullYear() }
        }
        const dateRange = parseAccountingDate(date_range, locale);
        offset = parseInt(offset?.value) || 0;
        dateRange.year += offset || 0;
        companyId = parseInt(companyId?.value) || null;
        try {
            includeUnposted = toBoolean(includeUnposted.value);
        } catch {
            includeUnposted = false;
        }
        const partnerIds = toString(partner_ids).split(",")

        const action = await env.services.orm.call(
            "account.account",
            "spreadsheet_move_line_action",
            [camelToSnakeObject({ dateRange, companyId, codes, includeUnposted, partnerIds })]
        );
        await env.services.action.doAction(action);
    },
    isVisible: (env) => {
        const position = env.model.getters.getActivePosition();
        const evaluatedCell = env.model.getters.getEvaluatedCell(position);
        const cell = env.model.getters.getCell(position);
        return (
            !isEvaluationError(evaluatedCell.value) &&
            evaluatedCell.value !== "" &&
            cell &&
            cell.isFormula &&
            getNumberOfAccountFormulas(cell.compiledFormula.tokens) === 1
        );
    },
});
