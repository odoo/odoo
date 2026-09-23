// @ts-check
/** @odoo-module native */

import { Component, onWillStart, onWillUpdateProps, useState, xml } from "@odoo/owl";
import { isX2ManyType } from "@web/core/field_types";
import { isObject, pick } from "@web/core/utils/collections/objects";
import { useService } from "@web/core/utils/hooks";
import { getFieldsSpec } from "@web/model/relational_model/field_spec";
import { RelationalModel } from "@web/model/relational_model/relational_model";

/** @import { Field, FieldInfo } from "@web/model/types" */

/** @import { LifecycleHooks, RelationalModelConfig, UIHooks } from "@web/model/relational_model/relational_model" */

/** @import { ServiceFactories } from "services" */

/**
 * @typedef {{
 * resModel: string;
 * resId?: number | false;
 * mode?: "edit" | "readonly";
 * context?: {[key: string]: any};
 * hooks?: { lifecycle?: Partial<LifecycleHooks>; ui?: Partial<UIHooks> };
 * activeFields?: {[key: string]: Partial<FieldInfo>};
 * fieldNames?: string[];
 * }} RecordInfo
 */

const defaultActiveField = { attrs: {}, options: {}, domain: "[]", string: "" };

class StandaloneRelationalModel extends RelationalModel {
    /**
     * @param {Partial<import("@web/model/types").SearchParams> & { values?: {[key: string]: any} }} [params]
     * @returns {Promise<void>}
     */
    async load(params = {}) {
        if (!params.values) {
            return super.load(params);
        }
        const config = this._getNextConfig(this.config, params);
        this.notifyLifecycleSync("onWillLoadRoot", config);
        this.root = this._createRoot(config, params.values);
        this.config = config;
        this.isReady = true;
        await this.notifyLifecycle("onRootLoaded", this.root);
    }
}

/**
 * @param {ServiceFactories["orm"]} orm
 * @param {{[key: string]: any}} activeField
 * @param {string} resModel
 * @param {number[]} resIds
 * @returns {Promise<{[key: string]: any}[]>}
 */
async function readX2manyRows(orm, activeField, resModel, resIds) {
    const { activeFields, fields } = activeField.related;
    return orm.webRead(resModel, resIds, {
        context: activeField.context || {},
        specification: getFieldsSpec(activeFields, fields, {}),
    });
}

/**
 * @param {ServiceFactories["orm"]} orm
 * @param {{[key: string]: any}} activeField
 * @param {string} resModel
 * @param {number | [number, string?] | { id: number, display_name?: string }} value
 * @returns {Promise<{ id: number, display_name: string } | any>}
 */
async function completeMany2one(orm, activeField, resModel, value) {
    const readDisplayName = async (/** @type {number} */ resId) => {
        const records = await orm.webRead(resModel, [resId], {
            context: activeField.context || {},
            specification: { display_name: {} },
        });
        return records[0]?.display_name ?? "";
    };
    if (typeof value === "number") {
        return { id: value, display_name: await readDisplayName(value) };
    }
    if (Array.isArray(value)) {
        const [id, displayName] = value;
        return {
            id,
            display_name:
                displayName === undefined ? await readDisplayName(id) : displayName,
        };
    }
    if (isObject(value)) {
        const { id, display_name: displayName } = /** @type {any} */ (value);
        return {
            id,
            display_name:
                displayName === undefined ? await readDisplayName(id) : displayName,
        };
    }
    return value;
}

/**
 * @param {ServiceFactories["orm"]} orm
 * @param {{ fields: {[key: string]: any}, activeFields: {[key: string]: any} }} schema
 * @param {{[key: string]: any}} rawValues
 * @returns {Promise<{[key: string]: any}>}
 */
async function prepareValues(orm, { fields, activeFields }, rawValues) {
    const values = pick(rawValues, ...Object.keys(activeFields));
    const proms = [];
    for (const fieldName of Object.keys(values)) {
        const { type, relation } = fields[fieldName];
        const value = values[fieldName];
        if (
            isX2ManyType(type) &&
            value.length &&
            typeof value[0] === "number" &&
            activeFields[fieldName].related
        ) {
            proms.push(
                readX2manyRows(orm, activeFields[fieldName], relation, value).then(
                    (records) => {
                        values[fieldName] = records;
                    },
                ),
            );
        } else if (type === "many2one") {
            proms.push(
                completeMany2one(orm, activeFields[fieldName], relation, value).then(
                    (completed) => {
                        values[fieldName] = completed;
                    },
                ),
            );
        }
    }
    await Promise.all(proms);
    return values;
}

class _Record extends Component {
    static template = xml`<t t-slot="default" record="this.model.root"/>`;
    static props = ["slots", "info", "fields", "values?"];
    setup() {
        /** @type {ServiceFactories["orm"]} */
        this.orm = useService("orm");
        const modelParams = {
            config: {
                resModel: this.props.info.resModel,
                fields: this.props.fields,
                isMonoRecord: true,
                activeFields: this.getActiveFields(),
                resId: this.props.info.resId,
                mode: this.props.info.mode,
                context: this.props.info.context,
            },
            hooks: this.props.info.hooks,
        };
        const modelServices = Object.fromEntries(
            StandaloneRelationalModel.services.map((servName) => [
                servName,
                useService(/** @type {any} */ (servName)),
            ]),
        );
        modelServices.orm = this.orm;
        this.model = useState(
            new StandaloneRelationalModel(
                /** @type {import("@web/env").OdooEnv} */ (this.env),
                modelParams,
                modelServices,
            ),
        );

        const schema = {
            fields: this.props.fields,
            activeFields: modelParams.config.activeFields,
        };
        const prepareLoadWithValues = (/** @type {{[key: string]: any}} */ values) =>
            prepareValues(this.orm, schema, values);

        onWillStart(async () => {
            if (this.props.values) {
                const values = await prepareLoadWithValues(this.props.values);
                await this.model.load({ values });
            } else {
                await this.model.load();
            }
            this.model.whenReady.resolve();
        });
        onWillUpdateProps(async (nextProps) => {
            const params = {};
            if (nextProps.info.resId !== this.model.root.resId) {
                params.resId = nextProps.info.resId;
            }
            if (nextProps.values) {
                params.values = await prepareLoadWithValues(nextProps.values);
            }
            if (Object.keys(params).length) {
                return this.model.load(params);
            }
        });
    }

    /** @returns {{[key: string]: any}} */
    getActiveFields() {
        if (this.props.info.activeFields) {
            /** @type {{[key: string]: any}} */
            const activeFields = {};
            for (const [fName, fInfo] of Object.entries(this.props.info.activeFields)) {
                activeFields[fName] = { ...defaultActiveField, ...fInfo };
            }
            return activeFields;
        }
        return Object.fromEntries(
            this.props.info.fieldNames.map((/** @type {string} */ f) => [
                f,
                { ...defaultActiveField },
            ]),
        );
    }
}

export class Record extends Component {
    static template = xml`<_Record fields="fields" slots="props.slots" values="props.values" info="props" />`;
    static components = { _Record };
    static props = [
        "slots",
        "resModel?",
        "fieldNames?",
        "activeFields?",
        "fields?",
        "resId?",
        "mode?",
        "values?",
        "context?",
        "hooks?",
    ];
    static defaultProps = {
        context: {},
    };
    setup() {
        const { activeFields, fieldNames, fields, resModel } = this.props;
        if (!activeFields && !fieldNames) {
            throw Error(
                `Record props should have either a "activeFields" key or a "fieldNames" key`,
            );
        }
        if (!fields && (!fieldNames || !resModel)) {
            throw Error(
                `Record props should have either a "fields" key or a "fieldNames" and a "resModel" key`,
            );
        }
        if (fields) {
            this.fields = fields;
        } else {
            const fieldService = useService("field");
            onWillStart(async () => {
                this.fields = await fieldService.loadFields(resModel, {
                    fieldNames,
                });
            });
        }
    }
}
