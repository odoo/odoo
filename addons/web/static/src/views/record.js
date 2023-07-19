/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { Component, xml, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

const defaultActiveField = { attrs: {}, options: {}, domain: "[]", string: "" };

class StandaloneRelationalModel extends RelationalModel {
    load(params = {}) {
        if (params.values) {
            const data = params.values;
            if (params.mode) {
                this.config.mode = params.mode;
            }
            this.root = this._createRoot(this.config, data);
            return;
        }
        return super.load(params);
    }
}

class _Record extends Component {
    setup() {
        const resModel = this.props.info.resModel;
        const modelParams = {
            config: {
                resModel,
                fields: this.props.fields,
                isMonoRecord: true,
                activeFields: this.getActiveFields(),
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
        modelServices.orm = useService("orm");
        this.model = useState(new StandaloneRelationalModel(this.env, modelParams, modelServices));

        const loadWithValues = (values) => {
            values = pick(values, ...Object.keys(modelParams.config.activeFields));
            return this.model.load({ values });
        };
        onWillStart(() => {
            if (this.props.values) {
                return loadWithValues(this.props.values);
            } else {
                return this.model.load();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.values) {
                return loadWithValues(nextProps.values);
            } else if (nextProps.info.resId !== this.model.root.resId) {
                return this.model.root.load(nextProps.info.resId);
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
_Record.template = xml`<t t-slot="default" record="model.root"/>`;
_Record.props = ["slots", "info", "fields", "values?"];

export class Record extends Component {
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
Record.template = xml`<_Record fields="fields" slots="props.slots" values="props.values" info="props" />`;
Record.components = { _Record };
Record.props = [
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
