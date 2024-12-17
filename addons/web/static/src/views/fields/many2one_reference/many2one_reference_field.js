import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "../many2one/many2one";
import { extractM2OFieldProps, Many2OneField } from "../many2one/many2one_field";

export class Many2OneReferenceField extends Component {
    static template = "web.Many2OneReferenceField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        const props = this.m2o.computeProps();

        const relation = this.relation;
        const value = this.props.record.data[this.props.name];
        return {
            ...props,
            relation,
            value: value ? [value.resId, value.displayName] : false,
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

    update(changes) {
        let nextVal;
        if (changes[this.props.name]) {
            nextVal = {
                resId: changes[this.props.name][0],
                displayName: changes[this.props.name][1],
            };
        } else {
            nextVal = false;
        }
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
