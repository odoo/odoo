/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";

import { Component } from "@odoo/owl";
import { containsReferences } from "@spreadsheet/helpers/helpers";

const { autofillModifiersRegistry, autofillRulesRegistry } = spreadsheet.registries;

//--------------------------------------------------------------------------
// Autofill Component
//--------------------------------------------------------------------------
export class AutofillTooltip extends Component {}
AutofillTooltip.template = "spreadsheet_edition.AutofillTooltip";
AutofillTooltip.props = { content: Array };

//--------------------------------------------------------------------------
// Autofill Rules
//--------------------------------------------------------------------------

autofillRulesRegistry
    .add("autofill_pivot", {
        condition: (cell) =>
            cell &&
            cell.isFormula &&
            cell.content.match(/=\s*ODOO\.PIVOT/) &&
            !containsReferences(cell),
        generateRule: (cell, cells) => {
            const increment = cells.filter(
                (cell) => cell && cell.isFormula && cell.content.match(/=\s*ODOO\.PIVOT/)
            ).length;
            return { type: "PIVOT_UPDATER", increment, current: 0 };
        },
        sequence: 2,
    })
    .add("autofill_pivot_position", {
        condition: (cell) =>
            cell && cell.isFormula && cell.content.match(/=.*ODOO\.PIVOT.*ODOO\.PIVOT\.POSITION/),
        generateRule: () => ({ type: "PIVOT_POSITION_UPDATER", current: 0 }),
        sequence: 1,
    });

//--------------------------------------------------------------------------
// Autofill Modifier
//--------------------------------------------------------------------------

autofillModifiersRegistry
    .add("PIVOT_UPDATER", {
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
            const content = getters.getPivotNextAutofillValue(data.cell.content, isColumn, steps);
            let tooltip = {
                props: {
                    content: data.content,
                },
            };
            if (content && content !== data.content) {
                tooltip = {
                    props: {
                        content: getters.getTooltipFormula(content, isColumn),
                    },
                    component: AutofillTooltip,
                };
            }
            if (!content) {
                tooltip = undefined;
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
    })
    .add("PIVOT_POSITION_UPDATER", {
        /**
         * Increment (or decrement) positions in template pivot formulas.
         * Autofilling vertically increments the field of the deepest row
         * group of the formula. Autofilling horizontally does the same for
         * column groups.
         */
        apply: (rule, data, getters, direction) => {
            const formulaString = data.cell.content;
            const pivotId = formulaString.match(/ODOO\.PIVOT\.POSITION\(\s*"(\w+)"\s*,/)[1];
            if (!getters.isExistingPivot(pivotId)) {
                return { cellData: { ...data.cell, content: formulaString } };
            }
            const pivotDefinition = getters.getPivotDefinition(pivotId);
            const fields = ["up", "down"].includes(direction)
                ? pivotDefinition.rowGroupBys
                : pivotDefinition.colGroupBys;
            const step = ["right", "down"].includes(direction) ? 1 : -1;

            const field = fields
                .reverse()
                .find((field) =>
                    new RegExp(`ODOO\\.PIVOT\\.POSITION.*${field}.*\\)`).test(formulaString)
                );
            const content = formulaString.replace(
                new RegExp(
                    `(.*ODOO\\.PIVOT\\.POSITION\\(\\s*"\\w"\\s*,\\s*"${field}"\\s*,\\s*"?)(\\d+)(.*)`
                ),
                (match, before, position, after) => {
                    rule.current += step;
                    return before + Math.max(parseInt(position) + rule.current, 1) + after;
                }
            );
            return {
                cellData: { ...data.cell, content },
                tooltip: content
                    ? {
                          props: { content },
                      }
                    : undefined,
            };
        },
    });
