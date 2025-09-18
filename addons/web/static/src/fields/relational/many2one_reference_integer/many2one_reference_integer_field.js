// @ts-check

/** @module @web/fields/relational/many2one_reference_integer/many2one_reference_integer_field - Integer display field for Many2oneReference columns showing the record ID */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { IntegerField } from "@web/fields/basic/integer/integer_field";

export class Many2OneReferenceIntegerField extends IntegerField {
    /** @returns {number|false} The referenced record's ID, or false if unset */
    get value() {
        const value = this.props.record.data[this.props.name];
        return value ? value.resId : false;
    }
}

const many2oneReferenceIntegerField = {
    component: Many2OneReferenceIntegerField,
    displayName: _t("Many2OneReferenceInteger"),
    supportedTypes: ["many2one_reference"],
};

registry
    .category("fields")
    .add("many2one_reference_integer", many2oneReferenceIntegerField);
