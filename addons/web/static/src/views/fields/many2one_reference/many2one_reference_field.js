import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "../many2one/many2one";
import { extractM2OFieldProps, Many2OneField } from "../many2one/many2one_field";

export class Many2OneReferenceField extends Component {
    static template = "web.Many2OneReferenceField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        const props = computeM2OProps(this.props);

        const relation = this.relation;
        const value = this.props.record.data[this.props.name];

        return {
            ...props,
            relation,
            value: value ? { id: value.resId, display_name: value.displayName } : false,
            readonly: this.props.readonly || !relation,
            update: (changes) => this.update(changes),
        };
    }

    get relation() {
        const modelField = this.props.record.fields[this.props.name].model_field;
        if (!(modelField in this.props.record.data)) {
            throw new Error(`Many2OneReferenceField: model_field must be in view (${modelField})`);
        }
        return this.props.record.data[modelField];
    }

    update(record) {
        const nextVal = record && { resId: record.id, displayName: record.display_name };
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
