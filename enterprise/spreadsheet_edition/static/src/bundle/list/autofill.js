/** @odoo-module */

import { getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";
import { containsReferences } from "@spreadsheet/helpers/helpers";
import * as spreadsheet from "@odoo/o-spreadsheet";

const { autofillModifiersRegistry, autofillRulesRegistry } = spreadsheet.registries;

//--------------------------------------------------------------------------
// Autofill Rules
//--------------------------------------------------------------------------

autofillRulesRegistry.add("autofill_list", {
    condition: (cell) =>
        cell &&
        cell.isFormula &&
        getNumberOfListFormulas(cell.compiledFormula.tokens) === 1 &&
        !containsReferences(cell),
    generateRule: (cell, cells) => {
        const increment = cells.filter(
            (cell) =>
                cell && cell.isFormula && getNumberOfListFormulas(cell.compiledFormula.tokens) === 1
        ).length;
        return { type: "LIST_UPDATER", increment, current: 0 };
    },
    sequence: 3,
});

//--------------------------------------------------------------------------
// Autofill Modifier
//--------------------------------------------------------------------------

autofillModifiersRegistry.add("LIST_UPDATER", {
    apply: (rule, data, getters, direction) => {
        rule.current += rule.increment;
        let isColumn;
        let steps;
        switch (direction) {
            case "up":
                isColumn = false;
                steps = -rule.current;
                break;
            case "down":
                isColumn = false;
                steps = rule.current;
                break;
            case "left":
                isColumn = true;
                steps = -rule.current;
                break;
            case "right":
                isColumn = true;
                steps = rule.current;
        }
        const content = getters.getNextListValue(data.cell.content, isColumn, steps);
        let tooltip = {
            props: {
                content,
            },
        };
        if (content && content !== data.content) {
            tooltip = {
                props: {
                    content: getters.getTooltipListFormula(content, isColumn),
                },
            };
        }
        return {
            cellData: {
                style: undefined,
                format: data.cell && data.cell.format,
                border: undefined,
                content,
            },
            tooltip,
        };
    },
});
