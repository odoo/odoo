// @ts-check
/** @odoo-module native */

import { onWillDestroy, toRaw, useState } from "@odoo/owl";
import { _t } from "@web/core/translation";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { registerField } from "@web/fields/_registry";
import { FieldComponent } from "@web/fields/field_component";
import { useRecordObserver } from "@web/fields/hooks/record_observer";
import {
    computeM2OProps,
    Many2One,
    stableM2OValue,
} from "@web/fields/relational/many2one/many2one";
import {
    extractM2OFieldProps,
    m2oSupportedAttributes,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/fields/relational/many2one/many2one_field";

/**
 * @typedef ReferenceValue
 * @property {string} resModel
 * @property {number} resId
 * @property {string} displayName
 */

export class ReferenceField extends FieldComponent {
    static template = "web.ReferenceField";
    static components = { Many2One };
    static props = {
        ...Many2OneField.props,
        hideModel: { type: Boolean, optional: true },
        modelField: { type: String, optional: true },
    };

    /** @type {{ formattedCharValue?: ReferenceValue | false, modelName?: string | false, currentRelation?: string | false }} */
    state;
    /** @type {number | undefined} */
    currentModelId;

    setup() {
        this.updateM2O = this.updateM2O.bind(this);
        this.state = useState({
            formattedCharValue: undefined,
            modelName: undefined,
            currentRelation: undefined,
        });
        this.nameService = useService("name");
        const keepLast = new KeepLast({ rejectSuperseded: true });
        onWillDestroy(() => keepLast.cancel());
        let currentRecord;
        const trackRecord = (record) => {
            const rawRecord = toRaw(record);
            if (rawRecord === currentRecord) {
                return false;
            }
            keepLast.cancel();
            currentRecord = rawRecord;
            return true;
        };

        const SUPERSEDED = Symbol("superseded");
        /**
         * @template T
         * @param {Promise<T>} promise
         * @returns {Promise<T | typeof SUPERSEDED>}
         */
        const latest = async (promise) => {
            try {
                return await keepLast.add(promise);
            } catch (error) {
                if (error instanceof SupersededError) {
                    return SUPERSEDED;
                }
                throw error;
            }
        };

        if (this._isCharField(this.props)) {
            /** @type {string | false | undefined} */
            let currentValue = undefined;
            useRecordObserver(async (record, props) => {
                if (trackRecord(record)) {
                    currentValue = undefined;
                }
                const requestedValue = record.data[props.name];
                if (currentValue !== requestedValue) {
                    const formatted = await latest(this._fetchReferenceCharData(props));
                    if (
                        formatted === SUPERSEDED ||
                        record.data[props.name] !== requestedValue
                    ) {
                        return;
                    }
                    this.state.formattedCharValue = formatted;
                    currentValue = requestedValue;
                }
            });
        } else if (this.props.modelField) {
            useRecordObserver(async (record, props) => {
                if (trackRecord(record)) {
                    this.currentModelId = undefined;
                    this.state.modelName = undefined;
                }
                const requestedModelId = record.data[props.modelField]?.id;
                if (this.currentModelId !== requestedModelId) {
                    const modelName = await latest(
                        this._fetchModelTechnicalName(props),
                    );
                    if (
                        modelName === SUPERSEDED ||
                        record.data[props.modelField]?.id !== requestedModelId
                    ) {
                        return;
                    }
                    this.state.modelName = modelName;
                    if (this.currentModelId !== undefined) {
                        record.update({ [props.name]: false });
                    }
                    this.currentModelId = requestedModelId;
                }
            });
        }
    }

    /** @returns {Object} */
    get m2oProps() {
        const value = this.getValue();
        const props = {
            ...computeM2OProps(this.props),
            relation: this.getRelation(),
            value: stableM2OValue(
                this.props,
                value && { id: value.resId, display_name: value.displayName },
            ),
            update: this.updateM2O,
        };
        if (this._isCharField(this.props)) {
            props.canQuickCreate = false;
        }
        return props;
    }
    /** @returns {Array<[string, string]>} */
    get selection() {
        if (!this._isCharField(this.props) && !this.hideModelSelector) {
            return this.field.definition.selection;
        }
        return [];
    }

    /** @returns {boolean|string} */
    get hideModelSelector() {
        return this.props.hideModel || this.props.modelField;
    }

    /** @returns {string | false | undefined} */
    getRelation() {
        const modelName = this.getModelName();
        if (modelName) {
            return modelName;
        }

        const value = /** @type {any} */ (this.getValue());
        if (value?.resModel) {
            return value.resModel;
        } else {
            return this.state.currentRelation;
        }
    }

    /** @returns {ReferenceValue|false} */
    getValue() {
        if (this._isCharField(this.props)) {
            return this.state.formattedCharValue;
        } else {
            return this.field.value;
        }
    }

    /** @returns {string | false | undefined} */
    getModelName() {
        return this.hideModelSelector && this.state.modelName;
    }

    /** @param {string} value */
    updateModel(value) {
        this.state.currentRelation = value;
        this.field.update(false);
    }

    /** @param {{ id: number, display_name: string }|false} value */
    updateM2O(value) {
        const resModel = this.getRelation();
        if (this._isCharField(this.props)) {
            this.field.update(value ? `${resModel},${value.id}` : false);
            return;
        }
        this.field.update(
            value && {
                resModel,
                resId: value.id,
                displayName: value.display_name,
            },
        );
    }

    _isCharField(/** @type {any} */ props) {
        return props.record.fields[props.name].type === "char";
    }

    /** @returns {Promise<{ resId: number, resModel: string, displayName: string }|false>} */
    async _fetchReferenceCharData(/** @type {any} */ props) {
        const recordData = props.record.data[props.name];
        if (!recordData) {
            return false;
        }
        const [resModel, _resId] = recordData.split(",");
        const resId = Number.parseInt(_resId, 10);
        if (!resModel || !resId) {
            return false;
        }
        const displayNames = await this.nameService.loadDisplayNames(resModel, [resId]);
        const displayName = displayNames[resId];
        if (typeof displayName !== "string") {
            return false;
        }
        return { resId, resModel, displayName };
    }

    _assertMany2OneToIrModel(/** @type {any} */ props) {
        const field = props.modelField && props.record.fields[props.modelField];
        if (field && (field.type !== "many2one" || field.relation !== "ir.model")) {
            throw new Error(
                `The model_field (${props.modelField}) of the reference field ${props.name} must be a many2one('ir.model').`,
            );
        }
    }

    /** @returns {Promise<string|false>} */
    async _fetchModelTechnicalName(/** @type {any} */ props) {
        this._assertMany2OneToIrModel(props);
        const record = props.record;
        const modelId = record.data[props.modelField]?.id;
        if (!modelId) {
            return false;
        }
        const { specialDataCaches, orm } = props.record.model;
        const key = `__reference__ir_model-${modelId}`;
        if (!specialDataCaches.has(key)) {
            specialDataCaches.set(
                key,
                orm
                    .read("ir.model", [modelId], ["model"])
                    .catch((/** @type {any} */ e) => {
                        specialDataCaches.delete(key);
                        throw e;
                    }),
            );
        }
        const result = await specialDataCaches.get(key);
        return result[0]?.model ?? false;
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
export const referenceField = {
    component: ReferenceField,
    displayName: _t("Reference"),
    supportedOptions: [
        ...m2oSupportedOptions,
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
    supportedAttributes: m2oSupportedAttributes,
    supportedTypes: ["reference", "char"],
    fieldDependencies: ({ options }) =>
        options.model_field
            ? [{ name: options.model_field, optional: true, readonly: true }]
            : [],
    extractProps(staticInfo, dynamicInfo) {
        const { options } = staticInfo;
        const props = extractM2OFieldProps(staticInfo, dynamicInfo);
        props.hideModel = !!options.hide_model;
        props.modelField = options.model_field;
        return props;
    },
};

registerField("reference", referenceField);
