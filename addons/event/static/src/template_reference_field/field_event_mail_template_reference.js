/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { ReferenceField, referenceField } from "@web/views/fields/reference/reference_field";

/**
 * @typedef ReferenceValue
 * @property {string} resModel
 * @property {number} resId
 * @property {string} displayName
 */

/**
 * 1. Reference field is a char field
 * 2. Reference widget has model_field prop
 * 3. Standard case
 */

/**
 * This class represents a reference field widget. It can be used to display
 * a reference field OR a char field.
 * The res_model of the relation is defined either by the reference field itself
 * or by the model_field prop.
 *
 * 1) Reference field is a char field
 * We have to fetch the display name (name_get) of the referenced record.
 *
 * 2) Reference widget has model_field prop
 * We have to fetch the technical name of the co model.
 *
 * 3) Standard case
 * The value is already in record.data[fieldName]
 */
export class EventMailTemplateReferenceField extends ReferenceField {
    static template = "event.mail_template_reference_field";
    static components = {
        Many2OneField,
    };
    get m2oProps() {
        const props = super.m2oProps;
        // makes editing in the list view much easier
        return { ...props, canOpen: false };
    }
}

export const eventMailTemplateReferenceField = {
    ...referenceField,
    component: EventMailTemplateReferenceField,
    displayName: _t("Event Mail Template Reference"),
};

registry
    .category("fields")
    .add("event_mail_template_reference_field", eventMailTemplateReferenceField);
