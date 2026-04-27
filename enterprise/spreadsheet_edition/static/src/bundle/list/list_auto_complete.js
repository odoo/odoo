/** @odoo-module */

import { registries, tokenColors, helpers } from "@odoo/o-spreadsheet";
import { extractDataSourceId } from "@spreadsheet/helpers/odoo_functions_helpers";

const { insertTokenAfterArgSeparator, insertTokenAfterLeftParenthesis, makeFieldProposal } =
    helpers;

registries.autoCompleteProviders.add("list_fields", {
    sequence: 50,
    autoSelectFirstProposal: true,
    getProposals(tokenAtCursor) {
        if (
            canAutoCompleteListField(tokenAtCursor) ||
            canAutoCompleteListHeaderField(tokenAtCursor)
        ) {
            const listId = extractDataSourceId(tokenAtCursor);
            if (!this.getters.isExistingList(listId)) {
                return;
            }
            const dataSource = this.getters.getListDataSource(listId);
            if (!dataSource.isMetaDataLoaded()) {
                return;
            }
            const fields = Object.values(dataSource.getFields());
            return fields.map((field) => makeFieldProposal(field));
        }
        return;
    },
    selectProposal: insertTokenAfterArgSeparator,
});

function canAutoCompleteListField(tokenAtCursor) {
    const functionContext = tokenAtCursor.functionContext;
    return (
        functionContext?.parent.toUpperCase() === "ODOO.LIST" && functionContext.argPosition === 2 // the field is the third argument: =ODOO.LIST(1,2,"email")
    );
}

function canAutoCompleteListHeaderField(tokenAtCursor) {
    const functionContext = tokenAtCursor.functionContext;
    return (
        functionContext?.parent.toUpperCase() === "ODOO.LIST.HEADER" &&
        functionContext.argPosition === 1 // the field is the second argument: =ODOO.LIST.HEADER(1,"email")
    );
}

registries.autoCompleteProviders.add("list_ids", {
    sequence: 50,
    autoSelectFirstProposal: true,
    getProposals(tokenAtCursor) {
        const functionContext = tokenAtCursor.functionContext;
        if (
            ["ODOO.LIST", "ODOO.LIST.HEADER"].includes(functionContext?.parent.toUpperCase()) &&
            functionContext.argPosition === 0
        ) {
            const listIds = this.getters.getListIds();
            return listIds.map((listId) => {
                const definition = this.getters.getListDefinition(listId);
                const str = `${listId}`;
                return {
                    text: str,
                    description: definition.name,
                    htmlContent: [{ value: str, color: tokenColors.NUMBER }],
                    fuzzySearchKey: str + definition.name,
                };
            });
        }
    },
    selectProposal: insertTokenAfterLeftParenthesis,
});
