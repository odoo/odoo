import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { getFieldsSpec } from "@web/model/relational_model/utils";
import { Component, xml, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

const defaultActiveField = { attrs: {}, options: {}, domain: "[]", string: "" };

class StandaloneRelationalModel extends RelationalModel {
    load(params = {}) {
        if (params.values) {
            const data = params.values;
            const config = this._getNextConfig(this.config, params);
            this.root = this._createRoot(config, data);
            this.config = config;
            return;
        }
        return super.load(params);
    }
}

class _Record extends Component {
    static template = xml`<t t-slot="default" record="model.root"/>`;
    static props = ["slots", "info", "fields", "values?"];
    setup() {
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
            },
            hooks: {
                onRecordSaved: this.props.info.onRecordSaved || (() => {}),
                onWillSaveRecord: this.props.info.onWillSaveRecord || (() => {}),
                onRecordChanged: this.props.info.onRecordChanged || (() => {}),
            },
        };
        const modelServices = Object.fromEntries(
            StandaloneRelationalModel.services.map((servName) => {
                return [servName, useService(servName)];
            })
        );
        modelServices.orm = this.orm;
        this.model = useState(new StandaloneRelationalModel(this.env, modelParams, modelServices));

        const prepareLoadWithValues = async (values) => {
            values = pick(values, ...Object.keys(modelParams.config.activeFields));
            const proms = [];
            for (const fieldName in values) {
                if (["one2many", "many2many"].includes(this.props.fields[fieldName].type)) {
                    if (values[fieldName].length && typeof values[fieldName][0] === "number") {
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
                                this.orm.webRead(resModel, resIds, kwargs).then((records) => {
                                    values[fieldName] = records;
                                })
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
                        const records = await this.orm.webRead(resModel, [resId], kwargs);
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
                    }
                }
                await Promise.all(proms);
            }
            return values;
        };
        onWillStart(async () => {
            if (this.props.values) {
                const values = await prepareLoadWithValues(this.props.values);
                return this.model.load({ values });
            } else {
                return this.model.load();
            }
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

    getActiveFields() {
        if (this.props.info.activeFields) {
            const activeFields = {};
            for (const [fName, fInfo] of Object.entries(this.props.info.activeFields)) {
                activeFields[fName] = { ...defaultActiveField, ...fInfo };
            }
            return activeFields;
        }
        return Object.fromEntries(
            this.props.info.fieldNames.map((f) => [f, { ...defaultActiveField }])
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
        "onRecordChanged?",
        "onRecordSaved?",
        "onWillSaveRecord?",
    ];
    setup() {
        if (this.props.fields) {
            this.fields = this.props.fields;
        } else {
            const orm = useService("orm");
            onWillStart(async () => {
                this.fields = await orm.call(
                    this.props.resModel,
                    "fields_get",
                    [this.props.fieldNames],
                    {}
                );
            });
        }
    }
}
