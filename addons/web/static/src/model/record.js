// @ts-check

/** @module @web/model/record - Standalone OWL component for loading and displaying a single record */

import { Component, onWillStart, onWillUpdateProps, useState, xml } from "@odoo/owl";
import { isObject, pick } from "@web/core/utils/collections/objects";
import { useService } from "@web/core/utils/hooks";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { getFieldsSpec } from "@web/model/relational_model/utils";

/** @import { Field, FieldInfo } from "@web/search/search_model" */
/** @import { RelationalModelConfig } from "@web/model/relational_model/relational_model" */
/** @import { ServiceFactories } from "services" */

/**
 * @typedef {{
 *   resModel: string;
 *   resId?: number | false;
 *   mode?: "edit" | "readonly";
 *   context?: {[key: string]: any};
 *   hooks?: {[key: string]: Function};
 *   activeFields?: {[key: string]: Partial<FieldInfo>};
 *   fieldNames?: string[];
 * }} RecordInfo
 */

const defaultActiveField = { attrs: {}, options: {}, domain: "[]", string: "" };

class StandaloneRelationalModel extends RelationalModel {
    /**
     * Override that supports loading from provided values instead of fetching.
     *
     * @param {Partial<import("@web/search/search_model").SearchParams> & { values?: {[key: string]: any} }} [params]
     * @returns {Promise<void>}
     */
    load(params = {}) {
        if (params.values) {
            const data = params.values;
            const config = this._getNextConfig(this.config, params);
            this.root = this._createRoot(config, data);
            this.config = config;
            this.hooks.onRootLoaded(this.root);
            return Promise.resolve();
        }
        return super.load(params);
    }
}

class _Record extends Component {
    static template = xml`<t t-slot="default" record="model.root"/>`;
    static props = ["slots", "info", "fields", "values?"];
    setup() {
        /** @type {ServiceFactories["orm"]} */
        this.orm = useService("orm");
        const resModel = this.props.info.resModel;
        const activeFields = this.getActiveFields();
        const modelParams = {
            config: {
                resModel,
                fields: this.props.fields,
                isMonoRecord: true,
                activeFields,
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
            new StandaloneRelationalModel(this.env, modelParams, modelServices),
        );

        /**
         * Resolve relational field values (many2one, x2many) by fetching
         * display names and nested records from the server.
         *
         * @param {{[key: string]: any}} values
         * @returns {Promise<{[key: string]: any}>}
         */
        const prepareLoadWithValues = async (values) => {
            values = pick(values, ...Object.keys(modelParams.config.activeFields));
            const proms = [];
            for (const fieldName in values) {
                if (
                    ["one2many", "many2many"].includes(
                        this.props.fields[fieldName].type,
                    )
                ) {
                    if (
                        values[fieldName].length &&
                        typeof values[fieldName][0] === "number"
                    ) {
                        const resModel = this.props.fields[fieldName].relation;
                        const resIds = values[fieldName];
                        const activeField = modelParams.config.activeFields[fieldName];
                        if (activeField.related) {
                            const { activeFields, fields } = activeField.related;
                            const fieldSpec = getFieldsSpec(activeFields, fields, {});
                            const kwargs = {
                                context: activeField.context || {},
                                specification: fieldSpec,
                            };
                            proms.push(
                                this.orm
                                    .webRead(resModel, resIds, kwargs)
                                    .then((records) => {
                                        values[fieldName] = records;
                                    }),
                            );
                        }
                    }
                }
                if (this.props.fields[fieldName].type === "many2one") {
                    const loadDisplayName = async (resId) => {
                        const resModel = this.props.fields[fieldName].relation;
                        const activeField = modelParams.config.activeFields[fieldName];
                        const kwargs = {
                            context: activeField.context || {},
                            specification: { display_name: {} },
                        };
                        const records = await this.orm.webRead(
                            resModel,
                            [resId],
                            kwargs,
                        );
                        return records[0].display_name;
                    };
                    if (typeof values[fieldName] === "number") {
                        const prom = loadDisplayName(values[fieldName]);
                        prom.then((displayName) => {
                            values[fieldName] = {
                                id: values[fieldName],
                                display_name: displayName,
                            };
                        });
                        proms.push(prom);
                    } else if (Array.isArray(values[fieldName])) {
                        if (values[fieldName][1] === undefined) {
                            const prom = loadDisplayName(values[fieldName][0]);
                            prom.then((displayName) => {
                                values[fieldName] = {
                                    id: values[fieldName][0],
                                    display_name: displayName,
                                };
                            });
                            proms.push(prom);
                        }
                        values[fieldName] = {
                            id: values[fieldName][0],
                            display_name: values[fieldName][1],
                        };
                    } else if (isObject(values[fieldName])) {
                        if (values[fieldName].display_name === undefined) {
                            const prom = loadDisplayName(values[fieldName].id);
                            prom.then((displayName) => {
                                values[fieldName] = {
                                    id: values[fieldName].id,
                                    display_name: displayName,
                                };
                            });
                            proms.push(prom);
                        }
                        values[fieldName] = {
                            id: values[fieldName].id,
                            display_name: values[fieldName].display_name,
                        };
                    }
                }
                await Promise.all(proms);
            }
            return values;
        };
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

    /**
     * Build the activeFields map from props, filling defaults.
     *
     * @returns {{[key: string]: any}}
     */
    getActiveFields() {
        if (this.props.info.activeFields) {
            const activeFields = {};
            for (const [fName, fInfo] of Object.entries(this.props.info.activeFields)) {
                activeFields[fName] = { ...defaultActiveField, ...fInfo };
            }
            return activeFields;
        }
        return Object.fromEntries(
            this.props.info.fieldNames.map((f) => [f, { ...defaultActiveField }]),
        );
    }
}

/**
 * Public Record component that resolves field definitions and delegates
 * to _Record for model instantiation.
 */
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
