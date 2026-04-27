/** @odoo-module */

import { registries, tokenColors, helpers } from "@odoo/o-spreadsheet";
const { insertTokenAfterLeftParenthesis } = helpers;

registries.autoCompleteProviders.add("global_filters", {
    sequence: 50,
    autoSelectFirstProposal: true,
    getProposals(tokenAtCursor) {
        const functionContext = tokenAtCursor.functionContext;
        if (
            functionContext?.parent.toUpperCase() === "ODOO.FILTER.VALUE" &&
            functionContext.argPosition === 0
        ) {
            const labels = this.getters.getGlobalFilters().map((filter) => filter.label);
            return labels.map((label) => {
                const escapedLabel = label.replaceAll('"', '\\"');
                const quotedLabel = `"${escapedLabel}"`;
                return {
                    text: quotedLabel,
                    htmlContent: [{ value: quotedLabel, color: tokenColors.STRING }],
                };
            });
        }
        return;
    },
    selectProposal: insertTokenAfterLeftParenthesis,
});
