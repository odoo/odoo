import { Component, proxy, t, untrack, useEffect, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { SelectMenu } from "@web/core/select_menu/select_menu";
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
    static components = { Many2One, SelectMenu };

    props = useProps(referenceFieldProps);

    setup() {
        this.isCharField = this.props.record.fields[this.props.name].type === "char";
        /** @type {{formattedCharValue?: ReferenceValue, currentRelation?: string}} */
        this.state = proxy({
            formattedCharValue: undefined, // Value extracted from reference char field
            currentRelation: undefined, // Model set by the model field, the model selector or the value
        });
        const { model } = this.props.record;
        useBus(model.bus, "WILL_SAVE_URGENTLY", () => this.validate());
        useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) => detail.proms.push(this.validate()));
        if (this.isCharField) {
            this._useCharValue();
        } else if (this.props.modelField) {
            this._useModelField();
        } else {
            this._useCurrentRelationSync();
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
        if (!this.isCharField && !this.hideModelSelector) {
            return this.props.record.fields[this.props.name].selection;
        }
        return [];
    }
    get choices() {
        return this.selection.map(([value, label]) => ({ value, label }));
    }

    get hideModelSelector() {
        return this.props.hideModel || this.props.modelField;
    }

    get modelPlaceholder() {
        return _t("Select a model...");
    }

    get recordPlaceholder() {
        return _t("Search a record...");
    }

    /**
     * @returns {ReferenceValue}
     */
    getValue() {
        return this.isCharField
            ? this.state.formattedCharValue
            : this.props.record.data[this.props.name];
    }

    /**
     * @returns {string|undefined}
     */
    getRelation() {
        return this.state.currentRelation || this.getValue()?.resModel;
    }

    validate() {
        const resModel = this.getRelation();
        const recordData = this.props.record.data[this.props.name];
        if (resModel && !recordData) {
            this.props.record.setInvalidField(this.props.name);
        }
    }

    updateModel(value) {
        this.state.currentRelation = value;
        this.props.record.update({ [this.props.name]: false });
    }

    updateM2O(value) {
        this.props.record.update({
            [this.props.name]: value && {
                resModel: this.getRelation(),
                resId: value.id,
                displayName: value.display_name,
            },
        });
    }

    /**
     * Fetch the display name of the record referenced by the field
     */
    _useCharValue() {
        let currentValue = undefined;
        useRecordObserver(async (record) => {
            const recordValue = record.data[this.props.name];
            if (currentValue !== recordValue) {
                this.state.formattedCharValue = await this._fetchReferenceCharData(recordValue);
                currentValue = recordValue;
            }
        });
    }

    /**
     * Fetch the technical name of the co model
     */
    _useModelField() {
        let currentModelId = undefined;
        useRecordObserver(async (record) => {
            const { modelField, name } = this.props;
            const recordId = record.data[modelField]?.id;
            if (currentModelId !== recordId) {
                this.state.currentRelation = await this._fetchModelTechnicalName(recordId);
                if (currentModelId !== undefined) {
                    record.update({ [name]: false });
                }
                currentModelId = recordId;
            }
        });
    }

    /**
     * Sync the currentRelation with current value's resModel
     */
    _useCurrentRelationSync() {
        useEffect(() => {
            const resModel = this.props.record.data[this.props.name]?.resModel;
            if (resModel && untrack(() => this.state.currentRelation) !== resModel) {
                this.state.currentRelation = resModel;
            }
        });
    }

    /**
     * Fetch special data if the reference field is a char field.
     * It fetches the display name of the record.
     */
    async _fetchReferenceCharData(recordData) {
        if (!recordData) {
            return false;
        }
        const [resModel, _resId] = recordData.split(",");
        const resId = parseInt(_resId, 10);
        if (resModel && resId) {
            const key = `__reference__name_get-${recordData}`;
            return {
                resId,
                resModel,
                displayName: await this._readOnce(key, resModel, resId, "display_name"),
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
    async _fetchModelTechnicalName(modelId) {
        this._assertMany2OneToIrModel();
        if (!modelId) {
            return false;
        }
        const key = `__reference__ir_model-${modelId}`;
        return this._readOnce(key, "ir.model", modelId, "model");
    }

    async _readOnce(key, resModel, resId, fieldName) {
        const { specialDataCaches, orm } = this.props.record.model;
        if (!specialDataCaches[key]) {
            specialDataCaches[key] = orm.read(resModel, [resId], [fieldName]);
        }
        const result = await specialDataCaches[key];
        return result[0][fieldName];
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
