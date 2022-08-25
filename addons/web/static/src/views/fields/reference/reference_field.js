/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2OneField } from "../many2one/many2one_field";

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
                valuesEqual(this.getValue(this.props) || {}, this.getValue(nextProps) || {}) &&
                this.getRelation(nextProps) !== this.state.resModel
            ) {
                nextProps.update(false);
            }
        });
    }

    getPreloadedData(p) {
        return p.record.preloadedData[p.name];
    }
    getValue(p) {
        if (p.type === "char") {
            return {
                resModel: this.getPreloadedData(p).model,
                resId: this.getPreloadedData(p).data.id,
                displayName: this.getPreloadedData(p).data.display_name,
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
    ...Many2OneField.props,
    hideModelSelector: { type: Boolean, optional: true },
};
ReferenceField.defaultProps = {
    ...Many2OneField.defaultProps,
};

ReferenceField.displayName = _lt("Reference");
ReferenceField.supportedTypes = ["reference", "char"];

ReferenceField.extractProps = ({ attrs, field }) => {
    return {
        ...Many2OneField.extractProps({ attrs, field }),
        hideModelSelector: !!attrs.options["model_field"],
    };
};

registry.category("fields").add("reference", ReferenceField);
