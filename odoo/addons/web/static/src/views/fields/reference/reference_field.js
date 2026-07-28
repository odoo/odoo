/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { many2OneField, Many2OneField } from "../many2one/many2one_field";

import { Component, useState } from "@odoo/owl";

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
export class ReferenceField extends Component {
    static template = "web.ReferenceField";
    static components = {
        Many2OneField,
    };
    static props = {
        ...Many2OneField.props,
        hideModel: { type: Boolean, optional: true },
        modelField: { type: String, optional: true },
    };
    static defaultProps = {
        ...Many2OneField.defaultProps,
    };

    setup() {
        /** @type {{formattedCharValue?: ReferenceValue, modelName?: string}} */
        this.state = useState({
            formattedCharValue: undefined, // Value extracted from reference char field
            modelName: undefined, // Name get of the value of the model field
            currentRelation: undefined,
        });
        if (this._isCharField(this.props)) {
            /** Fetch the display name of the record referenced by the field */
            let currentValue = undefined;
            useRecordObserver(async (record, props) => {
                if (currentValue !== record.data[props.name]) {
                    this.state.formattedCharValue = await this._fetchReferenceCharData(props);
                    currentValue = record.data[props.name];
                }
            });
        } else if (this.props.modelField) {
            /** Fetch the technical name of the co model */
            useRecordObserver(async (record, props) => {
                if (this.currentModelId !== record.data[props.modelField]?.[0]) {
                    this.state.modelName = await this._fetchModelTechnicalName(props);
                    if (this.currentModelId !== undefined) {
                        record.update({ [props.name]: false });
                    }
                    this.currentModelId = record.data[props.modelField]?.[0];
                }
            });
        }
    }

    get m2oProps() {
        const value = this.getValue();
        const p = {
            ...this.props,
            relation: this.getRelation(),
            value: value && [value.resId, value.displayName],
            update: this.updateM2O.bind(this),
        };
        delete p.hideModel;
        delete p.modelField;
        return p;
    }
    get selection() {
        if (!this._isCharField(this.props) && !this.hideModelSelector) {
            return this.props.record.fields[this.props.name].selection;
        }
        return [];
    }

    get relation() {
        return this.getRelation();
    }

    get hideModelSelector() {
        return this.props.hideModel || this.props.modelField;
    }

    getRelation() {
        const modelName = this.getModelName();
        if (modelName) {
            return modelName;
        }

        const value = this.getValue();
        if (value && value.resModel) {
            return value.resModel;
        } else {
            return this.state.currentRelation;
        }
    }

    /**
     * @returns {ReferenceValue|false}
     */
    getValue() {
        if (this._isCharField(this.props)) {
            return this.state.formattedCharValue;
        } else {
            return this.props.record.data[this.props.name];
        }
    }

    /**
     * @returns {string|undefined}
     */
    getModelName() {
        return this.hideModelSelector && this.state.modelName;
    }

    updateModel(value) {
        this.state.currentRelation = value;
        this.props.record.update({ [this.props.name]: false });
    }

    updateM2O(data) {
        const value = data[this.props.name];
        const resModel = this.state.currentRelation || this.getRelation();
        this.props.record.update({
            [this.props.name]: value && {
                resModel,
                resId: value[0],
                displayName: value[1],
            },
        });
    }

    /**
     * Return true if the reference field is a char field.
     */
    _isCharField(props) {
        return props.record.fields[props.name].type === "char";
    }

    /**
     * Fetch special data if the reference field is a char field.
     * It fetches the display name of the record.
     *
     * @returns {Promise<{ resId: number, resModel: string, displayName: string }|false>}
     */
    async _fetchReferenceCharData(props) {
        const recordData = props.record.data[props.name];
        if (!recordData) {
            return false;
        }
        const [resModel, _resId] = recordData.split(",");
        const resId = parseInt(_resId, 10);
        if (resModel && resId) {
            const { specialDataCaches, orm } = props.record.model;
            const key = `__reference__name_get-${recordData}`;
            if (!specialDataCaches[key]) {
                specialDataCaches[key] = orm.read(resModel, [resId], ["display_name"]);
            }
            const result = await specialDataCaches[key];
            return {
                resId,
                resModel,
                displayName: result[0].display_name,
            };
        }
        return false;
    }

    /**
     * Ensure that the modelField is a many2one to ir.model
     */
    _assertMany2OneToIrModel(props) {
        const field = props.modelField && props.record.fields[props.modelField];
        if (field && (field.type !== "many2one" || field.relation !== "ir.model")) {
            throw new Error(
                `The model_field (${props.modelField}) of the reference field ${props.name} must be a many2one('ir.model').`
            );
        }
    }

    /**
     * Fetch the technical name of the model which is selected in the modelField
     * props
     *
     * @returns {Promise<string|false>}
     */
    async _fetchModelTechnicalName(props) {
        this._assertMany2OneToIrModel(props);
        const record = props.record;
        const modelId = record.data[props.modelField]?.[0];
        if (!modelId) {
            return false;
        }
        const { specialDataCaches, orm } = props.record.model;
        const key = `__reference__ir_model-${modelId}`;
        if (!specialDataCaches[key]) {
            specialDataCaches[key] = orm.read("ir.model", [modelId], ["model"]);
        }
        const result = await specialDataCaches[key];
        return result[0].model;
    }
}

export const referenceField = {
    component: ReferenceField,
    displayName: _t("Reference"),
    supportedOptions: [
        {
            label: _t("Hide model"),
            name: "hide_model",
            type: "boolean",
        },
        {
            label: _t("Model field"),
            name: "model_field",
            type: "field",
            availableTypes: ["many2one"],
        },
    ],
    supportedTypes: ["reference", "char"],
    extractProps({ options }) {
        /*
        1 - <field name="ref" options="{'model_field': 'model_id'}" />
        2 - <field name="ref" options="{'hide_model': True}" />
        3 - <field name="ref" options="{'model_field': 'model_id' 'hide_model': True}" />
        4 - <field name="ref"/>

        We want to display the model selector only in the 4th case.
        */
        const props = many2OneField.extractProps(...arguments);
        props.hideModel = !!options.hide_model;
        props.modelField = options.model_field;
        return props;
    },
};

registry.category("fields").add("reference", referenceField);
