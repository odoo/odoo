/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { Many2OneField } from "../many2one/many2one_field";
import { standardFieldProps } from "../standard_field_props";

const { Component, onWillUpdateProps, useState } = owl;

function valuesEqual(a, b) {
    return a.resId === b.resId && a.resModel === b.resModel;
}

export class ReferenceField extends Component {
    setup() {
        this.state = useState({
            resModel: this.relation,
        });

        onWillUpdateProps((nextProps) => {
            if (
                valuesEqual(this.props.value || {}, nextProps.value || {}) &&
                nextProps.modelFieldValue !== this.props.modelFieldValue
            ) {
                nextProps.update(false);
            }
        });
    }

    get m2oProps() {
        const p = {
            ...this.props,
            relation: this.relation,
            value: this.props.value && [this.props.value.resId, this.props.value.displayName],
            update: this.updateM2O.bind(this),
        };
        delete p.hideModelSelector;
        delete p.modelSelection;
        delete p.modelFieldValue;
        return p;
    }

    get relation() {
        if (this.props.modelFieldValue) {
            return this.props.modelFieldValue;
        } else if (this.props.value && this.props.value.resModel) {
            return this.props.value.resModel;
        } else {
            return this.state && this.state.resModel;
        }
    }

    updateModel(value) {
        this.state.resModel = value;
        this.props.update(false);
    }

    updateM2O(value) {
        if (!this.state.resModel) {
            this.state.resModel = this.relation;
        }
        this.props.update(
            value && {
                resModel: this.state.resModel,
                resId: value[0],
                displayName: value[1],
            }
        );
    }
}

ReferenceField.template = "web.ReferenceField";
ReferenceField.components = {
    Many2OneField,
};
ReferenceField.props = {
    ...standardFieldProps,
    hideModelSelector: { type: Boolean, optional: true },
    modelFieldValue: { type: String, optional: true },
    value: [
        Boolean,
        {
            type: Object,
            shape: {
                resModel: String,
                resId: Number,
                displayName: String,
            },
        },
    ],
    getContext: { type: Function, optional: true },
    getDomain: { type: Function, optional: true },
    modelSelection: { type: Array, optional: true },
    string: { type: String, optional: true },
};
ReferenceField.defaultProps = {
    getContext: () => ({}),
    getDomain: () => new Domain(),
};

ReferenceField.displayName = _lt("Reference");
ReferenceField.supportedTypes = ["reference", "char"];

ReferenceField.extractProps = (fieldName, record, attrs) => {
    let props = {};
    const preloadedData = record.preloadedData[fieldName];
    if (record.fields[fieldName].type === "char") {
        props = {
            value: {
                resModel: preloadedData.model,
                resId: preloadedData.data.id,
                displayName: preloadedData.data.display_name,
            },
        };
    } else if (attrs.options["model_field"]) {
        props = {
            hideModelSelector: true,
            modelFieldValue: preloadedData && preloadedData.modelName,
        };
    } else {
        props = {
            modelSelection: record.fields[fieldName].selection,
        };
    }

    return {
        ...props,
        getContext: () => record.getFieldContext(fieldName),
        getDomain: () => record.getFieldDomain(fieldName),
        string: attrs.string || record.fields[fieldName].string,
    };
};

registry.category("fields").add("reference", ReferenceField);
