/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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

const ODOO_LIST = {
    description: _t("Get the value from a list."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("index (string)", _t("Position of the record in the list.")),
        arg("field_name (string)", _t("Name of the field.")),
    ],
    category: "Odoo",
    compute: function (listId, index, fieldName) {
        const id = toString(listId);
        const position = toNumber(index, this.locale) - 1;
        const field = toString(fieldName);
        assertListsExists(id, this.getters);
        return this.getters.getListCellValue(id, position, field);
    },
    computeFormat: function (listId, index, fieldName) {
        const id = toString(listId.value);
        const position = toNumber(index.value, this.locale) - 1;
        const field = this.getters.getListDataSource(id).getField(toString(fieldName.value));
        switch (field.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary": {
                const currency = this.getters.getListCurrency(id, position, field.currency_field);
                if (!currency) {
                    return "#,##0.00";
                }
                return this.getters.computeFormatFromCurrency(currency);
            }
            case "date":
                return this.locale.dateFormat;
            case "datetime":
                return this.locale.dateFormat + " " + this.locale.timeFormat;
            default:
                return undefined;
        }
    },
    returns: ["NUMBER", "STRING"],
};

const ODOO_LIST_HEADER = {
    description: _t("Get the header of a list."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("field_name (string)", _t("Name of the field.")),
    ],
    category: "Odoo",
    compute: function (listId, fieldName) {
        const id = toString(listId);
        const field = toString(fieldName);
        assertListsExists(id, this.getters);
        return this.getters.getListHeaderValue(id, field);
    },
    returns: ["NUMBER", "STRING"],
};

functionRegistry.add("ODOO.LIST", ODOO_LIST);
functionRegistry.add("ODOO.LIST.HEADER", ODOO_LIST_HEADER);
