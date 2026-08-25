import { Component, computed, proxy, t, untrack, useEffect, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { computeM2OProps, Many2One } from "../many2one/many2one";
import { extractM2OFieldProps, many2OneFieldProps } from "../many2one/many2one_field";

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
export const referenceFieldProps = {
    ...many2OneFieldProps,
    hideModel: t.boolean().optional(),
    modelField: t.string().optional(),
};

export class ReferenceField extends Component {
    static template = "web.ReferenceField";
    static components = { Many2One };

    props = useProps(referenceFieldProps);

    isCharField = computed(() => this.props.record.fields[this.props.name].type === "char");

    /** @type {import("@odoo/owl").ReactiveValue<ReferenceValue>} */
    getValue = computed(() =>
        this.isCharField() ? this.state.formattedCharValue : this.props.record.data[this.props.name]
    );

    setup() {
        /** @type {{formattedCharValue?: ReferenceValue, modelName?: string}} */
        this.state = proxy({
            formattedCharValue: undefined, // Value extracted from reference char field
            modelName: undefined, // Name get of the value of the model field
            currentRelation: undefined,
        });
        if (this.isCharField()) {
            /** Fetch the display name of the record referenced by the field */
            let currentValue = undefined;
            useRecordObserver(async (record) => {
                const recordValue = record.data[this.props.name];
                if (currentValue !== recordValue) {
                    this.state.formattedCharValue = await this._fetchReferenceCharData();
                    currentValue = recordValue;
                }
            });
        } else if (this.props.modelField) {
            /** Fetch the technical name of the co model */
            useRecordObserver(async (record) => {
                const { modelField, name } = this.props;
                const recordId = record.data[modelField]?.id;
                if (this.currentModelId !== recordId) {
                    this.state.modelName = await this._fetchModelTechnicalName();
                    if (this.currentModelId !== undefined) {
                        record.update({ [name]: false });
                    }
                    this.currentModelId = recordId;
                }
            });
        } else {
            /** Sync the currentRelation with current value's resModel */
            useEffect(() => {
                const resModel = this.props.record.data[this.props.name]?.resModel;
                if (resModel && untrack(() => this.state.currentRelation) !== resModel) {
                    this.state.currentRelation = resModel;
                }
            });
        }
    }

    get m2oProps() {
        const value = this.getValue();
        return {
            ...computeM2OProps(this.props),
            relation: this.getRelation(),
            value: value && { id: value.resId, display_name: value.displayName },
            update: this.updateM2O.bind(this),
        };
    }
    get selection() {
        if (!this.isCharField() && !this.hideModelSelector) {
            return this.props.record.fields[this.props.name].selection;
        }
        return [];
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
     * @returns {string|undefined}
     */
    getModelName() {
        return this.hideModelSelector && this.state.modelName;
    }

    updateModel(value) {
        this.state.currentRelation = value;
        this.props.record.update({ [this.props.name]: false });
    }

    updateM2O(value) {
        const resModel = this.state.currentRelation || this.getRelation();
        this.props.record.update({
            [this.props.name]: value && {
                resModel,
                resId: value.id,
                displayName: value.display_name,
            },
        });
    }

    /**
     * Fetch special data if the reference field is a char field.
     * It fetches the display name of the record.
     */
    async _fetchReferenceCharData() {
        const recordData = this.props.record.data[this.props.name];
        if (!recordData) {
            return false;
        }
        const [resModel, _resId] = recordData.split(",");
        const resId = parseInt(_resId, 10);
        if (resModel && resId) {
            const { specialDataCaches, orm } = this.props.record.model;
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
    _assertMany2OneToIrModel() {
        const { modelField, name, record } = this.props;
        const field = modelField && record.fields[modelField];
        if (field && (field.type !== "many2one" || field.relation !== "ir.model")) {
            throw new Error(
                `The model_field (${modelField}) of the reference field ${name} must be a many2one('ir.model').`
            );
        }
    }

    /**
     * Fetch the technical name of the model which is selected in the modelField
     * props
     *
     * @returns {Promise<string|false>}
     */
    async _fetchModelTechnicalName() {
        this._assertMany2OneToIrModel();
        const { modelField, record } = this.props;
        const modelId = record.data[modelField]?.id;
        if (!modelId) {
            return false;
        }
        const { specialDataCaches, orm } = record.model;
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
        const props = extractM2OFieldProps(...arguments);
        props.hideModel = !!options.hide_model;
        props.modelField = options.model_field;
        return props;
    },
};

registry.category("fields").add("reference", referenceField);
