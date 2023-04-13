/** @odoo-module **/

import { _t } from "web.core";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { sprintf } from "@web/core/utils/strings";

const { arg, toString, toNumber } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

function assertListsExists(listId, getters) {
    if (!getters.isExistingList(listId)) {
        throw new Error(sprintf(_t('There is no list with id "%s"'), listId));
    }
}

functionRegistry.add("ODOO.LIST", {
    description: _t("Get the value from a list."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("index (string)", _t("Position of the record in the list.")),
        arg("field_name (string)", _t("Name of the field.")),
    ],
    compute: function (listId, index, fieldName) {
        const id = toString(listId);
        const position = toNumber(index) - 1;
        const field = toString(fieldName);
        assertListsExists(id, this.getters);
        return this.getters.getListCellValue(id, position, field);
    },
    computeFormat: function (listId, index, fieldName) {
        const id = toString(listId.value);
        const position = toNumber(index.value) - 1;
        const field = this.getters.getListDataSource(id).getField(toString(fieldName.value));
        switch (field.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary": {
                const currencyName = this.getters.getListCellValue(
                    id,
                    position,
                    field.currency_field
                );
                return this.getters.getCurrencyFormat(currencyName);
            }
            case "date":
                return "m/d/yyyy";
            case "datetime":
                return "m/d/yyyy hh:mm:ss";
            default:
                return undefined;
        }
    },
    returns: ["NUMBER", "STRING"],
});

functionRegistry.add("ODOO.LIST.HEADER", {
    description: _t("Get the header of a list."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("field_name (string)", _t("Name of the field.")),
    ],
    compute: function (listId, fieldName) {
        const id = toString(listId);
        const field = toString(fieldName);
        assertListsExists(id, this.getters);
        return this.getters.getListHeaderValue(id, field);
    },
    returns: ["NUMBER", "STRING"],
});
