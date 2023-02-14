/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { many2OneField, Many2OneField } from "../many2one/many2one_field";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

function valuesEqual(a, b) {
    return a.resId === b.resId && a.resModel === b.resModel;
}

export class ReferenceField extends Component {
    static template = "web.ReferenceField";
    static components = {
        Many2OneField,
    };
    static props = {
        ...Many2OneField.props,
        hideModelSelector: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...Many2OneField.defaultProps,
    };

    setup() {
        this.state = useState({
            resModel: this.relation,
        });

        onWillUpdateProps((nextProps) => {
            if (
                valuesEqual(this.getValue(this.props) || {}, this.getValue(nextProps) || {}) &&
                this.state.resModel &&
                this.getRelation(nextProps) !== this.state.resModel
            ) {
                nextProps.record.update({ [this.props.name]: false });
            }
        });
    }

    getPreloadedData(p) {
        return p.record.preloadedData[p.name];
    }
    getValue(p) {
        if (p.type === "char") {
            const pdata = this.getPreloadedData(p);
            if (!pdata) {
                return null;
            }
            return {
                resModel: pdata.model,
                resId: pdata.data.id,
                displayName: pdata.data.display_name,
            };
        } else {
            return p.value;
        }
    }
    get m2oProps() {
        const value = this.getValue(this.props);
        const p = {
            ...this.props,
            relation: this.relation,
            value: value && [value.resId, value.displayName],
            update: this.updateM2O.bind(this),
        };
        delete p.hideModelSelector;
        return p;
    }
    get selection() {
        if (this.props.type !== "char" && !this.props.hideModelSelector) {
            return this.props.record.fields[this.props.name].selection;
        }
        return [];
    }

    get relation() {
        return this.getRelation(this.props);
    }

    getRelation(props) {
        const modelName = this.getModelName(props);
        if (modelName) {
            return modelName;
        }

        const value = this.getValue(props);
        if (value && value.resModel) {
            return value.resModel;
        } else {
            return this.state && this.state.resModel;
        }
    }

    getModelName(p) {
        if (p.hideModelSelector && p.record.preloadedData[p.name]) {
            return p.record.preloadedData[p.name].modelName;
        }
        return null;
    }

    updateModel(value) {
        this.state.resModel = value;
        this.props.record.update({ [this.props.name]: false });
    }

    updateM2O(data) {
        const value = data[this.props.name];
        if (!this.state.resModel) {
            this.state.resModel = this.relation;
        }
        this.props.record.update({
            [this.props.name]: value && {
                resModel: this.state.resModel,
                resId: value[0],
                displayName: value[1],
            },
        });
    }
}

export const referenceField = {
    component: ReferenceField,
    displayName: _lt("Reference"),
    supportedTypes: ["reference", "char"],
    legacySpecialData: "_fetchSpecialReference",
    extractProps: (params) => ({
        /*
        1 - <field name="ref" options="{'model_field': 'model_id'}" />
        2 - <field name="ref" options="{'hide_model': True}" />
        3 - <field name="ref" options="{'model_field': 'model_id' 'hide_model': True}" />
        4 - <field name="ref"/>

        We want to display the model selector only in the 4th case.
        */
        ...many2OneField.extractProps(params),
        hideModelSelector:
            !!params.attrs.options["hide_model"] || !!params.attrs.options["model_field"],
    }),
};

registry.category("fields").add("reference", referenceField);
