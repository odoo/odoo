/** @odoo-module **/

import { Field } from "@web/views/fields/field";
import { patch } from "@web/core/utils/patch";

/**
 * Odoo 19 marks empty fields with `o_field_empty` only when they are rendered
 * readonly (see `fieldVisualFeedback`). In edit mode, an empty editable input
 * therefore carries no marker, which makes it impossible to style "the box that
 * has not been filled in yet" without touching fields that already hold a value.
 *
 * This patch adds `o_od19_field_empty` to empty field widgets while the record
 * is in edition, so the CSS (form_readability.css) can highlight empty slots
 * only. Fields that already have data are left untouched.
 */
patch(Field.prototype, {
    get classNames() {
        const classNames = super.classNames;
        const { name, record } = this.props;
        const field = this.field;
        if (field && record && name != null && record.isInEdition) {
            let empty;
            if ("isEmpty" in field) {
                empty = field.isEmpty(record, name);
            } else {
                const value = record.data[name];
                empty = value === false || value === "" || value == null;
            }
            classNames.o_od19_field_empty = !!empty;
        }
        return classNames;
    },
});
