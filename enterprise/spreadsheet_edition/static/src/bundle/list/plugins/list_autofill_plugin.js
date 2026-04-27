/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { astToFormula, UIPlugin, tokenize } from "@odoo/o-spreadsheet";
import { sprintf } from "@web/core/utils/strings";
import { getFirstListFunction, getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";

export class ListAutofillPlugin extends UIPlugin {
    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the next value to autofill of a list function
     *
     * @param {string} formula List formula
     * @param {boolean} isColumn True if autofill is LEFT/RIGHT, false otherwise
     * @param {number} increment number of steps
     *
     * @returns Autofilled value
     */
    getNextListValue(formula, isColumn, increment) {
        const tokens = tokenize(formula);
        if (getNumberOfListFormulas(tokens) !== 1) {
            return formula;
        }
        const { functionName, args } = getFirstListFunction(tokens);
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(this.getters.getActiveSheetId(), arg));
        const listId = evaluatedArgs[0];
        if (!this.getters.isExistingList(listId)) {
            return formula;
        }
        const columns = this.getters.getListDefinition(listId).columns;
        if (functionName === "ODOO.LIST") {
            const position = parseInt(evaluatedArgs[1], 10);
            const field = evaluatedArgs[2];
            if (isColumn) {
                /** Change the field */
                const index = columns.findIndex((col) => col === field) + increment;
                if (index < 0 || index >= columns.length) {
                    return "";
                }
                return this._getListFunction(listId, position, columns[index]);
            } else {
                /** Change the position */
                const nextPosition = position + increment;
                if (nextPosition === 0) {
                    return this._getListHeaderFunction(listId, field);
                }
                if (nextPosition < 0) {
                    return "";
                }
                return this._getListFunction(listId, nextPosition, field);
            }
        }
        if (functionName === "ODOO.LIST.HEADER") {
            const field = evaluatedArgs[1];
            if (isColumn) {
                /** Change the field */
                const index = columns.findIndex((col) => col === field) + increment;
                if (index < 0 || index >= columns.length) {
                    return "";
                }
                return this._getListHeaderFunction(listId, columns[index]);
            } else {
                /** If down, set position */
                if (increment > 0) {
                    return this._getListFunction(listId, increment, field);
                }
                return "";
            }
        }
        return formula;
    }

    /**
     * Compute the tooltip to display from a Pivot formula
     *
     * @param {string} formula Pivot formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     */
    getTooltipListFormula(formula, isColumn) {
        if (!formula) {
            return [];
        }
        const { functionName, args } = getFirstListFunction(tokenize(formula));
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(this.getters.getActiveSheetId(), arg));
        const listId = evaluatedArgs[0];
        if (!this.getters.isExistingList(listId)) {
            return sprintf(_t("Missing list #%s"), listId);
        }
        if (isColumn || functionName === "ODOO.LIST.HEADER") {
            const fieldName = functionName === "ODOO.LIST" ? evaluatedArgs[2] : evaluatedArgs[1];
            return this.getters.getListDataSource(listId).getListHeaderValue(fieldName);
        }
        return _t("Record #%(record_number)s", { record_number: evaluatedArgs[1] });
    }

    _getListFunction(listId, position, field) {
        return `=ODOO.LIST(${listId},${position},"${field}")`;
    }

    _getListHeaderFunction(listId, field) {
        return `=ODOO.LIST.HEADER(${listId},"${field}")`;
    }
}

ListAutofillPlugin.getters = ["getNextListValue", "getTooltipListFormula"];
