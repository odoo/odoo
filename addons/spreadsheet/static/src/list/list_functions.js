import { _t } from "@web/core/l10n/translation";
import { helpers, registries, EvaluationError } from "@odoo/o-spreadsheet";

const { arg, toString, toNumber } = helpers;
const { functionRegistry } = registries;

const MAX_LIMIT = 10_000;

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

function assertListsExists(listId, getters) {
    if (!getters.isExistingList(listId)) {
        throw new EvaluationError(_t('There is no list with id "%s"', listId));
    }
}

const ODOO_LIST_VALUE = {
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
        const _fieldName = toString(fieldName);
        if (!_fieldName) {
            return new EvaluationError(_t("The field name should not be empty."));
        }
        assertListsExists(id, this.getters);
        return this.getters.getListCellValueAndFormat(id, position, _fieldName);
    },
};

const ODOO_LIST_HEADER = {
    description: _t("Get the header of a list."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("field_name (string)", _t("Technical field name.")),
        arg("field_display_name (string, optional)", _t("Name of the field.")),
    ],
    category: "Odoo",
    compute: function (listId, fieldName, fieldDisplayName) {
        const id = toString(listId);
        const field = toString(fieldName);
        assertListsExists(id, this.getters);
        const displayName = toString(fieldDisplayName);
        return displayName || this.getters.getListHeaderValue(id, field);
    },
};

const ODOO_LIST = {
    description: _t("Get a dynamic Odoo list function."),
    args: [
        arg("list_id (string)", _t("ID of the list.")),
        arg("row_count (number, optional)", _t("number of rows to display")),
    ],
    category: "Odoo",
    compute: function (listId, rowCount) {
        const id = toString(listId);
        assertListsExists(id, this.getters);
        const _rowCount = rowCount ? toNumber(rowCount, this.locale) : undefined;
        if (_rowCount !== undefined && _rowCount <= 0) {
            return new EvaluationError(
                _t("The number of rows parameter should be a positive number.")
            );
        }
        const result = this.getters.getListValuesAndFormats(id, _rowCount ?? MAX_LIMIT);
        if (result[0]?.length > MAX_LIMIT && _rowCount === undefined) {
            return new EvaluationError(
                _t(
                    "the default maximum number of rows (%s) has been reached. Please explicitely set the row_count parameter.",
                    MAX_LIMIT
                )
            );
        }
        return result;
    },
};

functionRegistry.add("ODOO.LIST.VALUE", ODOO_LIST_VALUE);
functionRegistry.add("ODOO.LIST.HEADER", ODOO_LIST_HEADER);
functionRegistry.add("ODOO.LIST", ODOO_LIST);
