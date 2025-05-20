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
    async execute(env, newWindow) {
        const position = env.model.getters.getActivePosition();
        const sheetId = position.sheetId;
        const cell = env.model.getters.getCell(position);
        const func = getFirstAccountFunction(cell.compiledFormula.tokens);
        let codes, partner_ids, account_tag_ids = "";
        let date_range, offset, companyId, includeUnposted = false;
        const parsed_args = func.args.map(astToFormula).map(
            (arg) => env.model.getters.evaluateFormulaResult(sheetId, arg)
        );
        if ( func.functionName === "ODOO.PARTNER.BALANCE" ) {
            [partner_ids, codes, date_range, offset, companyId, includeUnposted] = parsed_args;
        } else if ( func.functionName === "ODOO.BALANCE.TAG" ) {
            [account_tag_ids, date_range, offset, companyId, includeUnposted] = parsed_args;
        } else {
            [codes, date_range, offset, companyId, includeUnposted] = parsed_args;
        }
        if ( codes?.value && !isEvaluationError(codes.value) ) {
            codes = toString(codes?.value).split(",").map((code) => code.trim());
        } else {
            codes = [];
        }
        const locale = env.model.getters.getLocale();
        let dateRange;
        if ( date_range?.value && !isEvaluationError(date_range.value) ) {
            dateRange = parseAccountingDate(date_range, locale);
        } else {
            if ( ["ODOO.PARTNER.BALANCE", "ODOO.RESIDUAL", "ODOO.BALANCE.TAG"].includes(func.functionName) ) {
                dateRange = parseAccountingDate({ value: new Date().getFullYear() }, locale);
            }
        }
        offset = parseInt(offset?.value) || 0;
        dateRange.year += offset || 0;
        companyId = parseInt(companyId?.value) || null;
        try {
            includeUnposted = toBoolean(includeUnposted.value);
        } catch {
            includeUnposted = false;
        }

        let partnerIds, accountTagIds;
        if ( func.functionName === "ODOO.BALANCE.TAG" ) {
            accountTagIds = toString(account_tag_ids).split(",").map((tag) => tag.trim());
        } else {
            partnerIds = toString(partner_ids).split(",").map((code) => code.trim());
        }

        let param;
        if ( func.functionName === "ODOO.BALANCE.TAG" ) {
            param = [camelToSnakeObject({ accountTagIds, dateRange, companyId, includeUnposted })]
        } else if ( func.functionName === "ODOO.PARTNER.BALANCE" ) {
            param = [camelToSnakeObject({ dateRange, companyId, codes, includeUnposted, partnerIds })]
        } else {
            param = [camelToSnakeObject({ dateRange, companyId, codes, includeUnposted })]
        }
        const action = await env.services.orm.call(
            "account.account",
            "spreadsheet_move_line_action",
            param
        );
        await env.services.action.doAction(action, { newWindow });
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
    icon: "o-spreadsheet-Icon.SEE_RECORDS",
});
