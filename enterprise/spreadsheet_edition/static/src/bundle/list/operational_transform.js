/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
const { otRegistry } = spreadsheet.registries;

otRegistry
    .addTransformation(
        "INSERT_ODOO_LIST",
        ["INSERT_ODOO_LIST", "DUPLICATE_ODOO_LIST"],
        transformNewListCommand
    )
    .addTransformation(
        "DUPLICATE_ODOO_LIST",
        ["INSERT_ODOO_LIST", "DUPLICATE_ODOO_LIST"],
        transformNewListCommand
    )
    .addTransformation(
        "REMOVE_ODOO_LIST",
        ["RENAME_ODOO_LIST", "UPDATE_ODOO_LIST_DOMAIN", "UPDATE_ODOO_LIST"],
        (toTransform, executed) => {
            if (toTransform.listId === executed.listId) {
                return undefined;
            }
            return toTransform;
        }
    )
    .addTransformation(
        "REMOVE_ODOO_LIST",
        ["RE_INSERT_ODOO_LIST", "DUPLICATE_ODOO_LIST"],
        (toTransform, executed) => {
            if (toTransform.id === executed.listId) {
                return undefined;
            }
            return toTransform;
        }
    );

function transformNewListCommand(toTransform) {
    const idKey = "newListId" in toTransform ? "newListId" : "id";
    return {
        ...toTransform,
        [idKey]: (parseInt(toTransform[idKey], 10) + 1).toString(),
    };
}
