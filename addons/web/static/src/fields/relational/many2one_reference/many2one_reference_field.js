// @ts-check

/** @module @web/fields/relational/many2one_reference/many2one_reference_field - Many2one field for Many2oneReference columns with dynamic relation model */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    extractM2OFieldProps,
    Many2OneField,
} from "@web/fields/relational/many2one/many2one_field";

export class Many2OneReferenceField extends Many2OneField {
    static template = "web.Many2OneReferenceField";

    /** @returns {Object} Props for the inner Many2One component */
    get m2oProps() {
        const relation = this.relation;
        const value = this.props.record.data[this.props.name];

        return {
            ...super.m2oProps,
            relation,
            value: value ? { id: value.resId, display_name: value.displayName } : false,
            readonly: this.props.readonly || !relation,
            update: (changes) => this.update(changes),
        };
    }

    /** @returns {string|false} Technical model name from the model_field */
    get relation() {
        const modelField = this.props.record.fields[this.props.name].model_field;
        if (!(modelField in this.props.record.data)) {
            throw new Error(
                `Many2OneReferenceField: model_field must be in view (${modelField})`,
            );
        }
        return this.props.record.data[modelField];
    }

    /** @param {{ id: number, display_name: string }|false} record */
    update(record) {
        const nextVal = record && {
            resId: record.id,
            displayName: record.display_name,
        };
        return this.props.record.update({ [this.props.name]: nextVal });
    }
}

registry.category("fields").add("many2one_reference", {
    component: Many2OneReferenceField,
    displayName: _t("Many2OneReference"),
    extractProps(staticInfo, dynamicInfo) {
        return extractM2OFieldProps(staticInfo, dynamicInfo);
    },
    relatedFields: [{ name: "display_name", type: "char" }],
    supportedTypes: ["many2one_reference"],
});
