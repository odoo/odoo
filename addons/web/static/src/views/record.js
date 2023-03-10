/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { RelationalModel } from "@web/views/relational_model/relational_model";
import { Component, xml, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

const defaultActiveField = { attrs: {}, options: {}, domain: "[]", string: "" };

class _Record extends Component {
    setup() {
        const resModel = this.props.info.resModel;
        const modelParams = {
            resModel,
            fields: this.props.fields,
            viewMode: "form",
            rootType: "record",
            activeFields: this.getActiveFields(),
        };
        const modelServices = Object.fromEntries(
            RelationalModel.services.map((servName) => {
                return [servName, useService(servName)];
            })
        );
        if (resModel) {
            modelServices.orm = useService("orm");
        }

        this.model = useState(new RelationalModel(this.env, modelParams, modelServices));

        let loadKey;
        const load = (props) => {
            const loadParams = {
                resId: props.info.resId,
                mode: props.info.mode,
            };
            if (props.values) {
                loadParams.values = pick(props.values, ...Object.keys(modelParams.activeFields));
            }
            const nextLoadKey = JSON.stringify(loadParams);
            if (loadKey === nextLoadKey) {
                return;
            }
            loadKey = nextLoadKey;
            return this.model.load(loadParams);
        };
        onWillStart(() => load(this.props));
        onWillUpdateProps((nextProps) => {
            // don't wait because the keeplast may make willUpdateProps hang forever
            load(nextProps);
        });

        if (this.props.info.onRecordChanged) {
            useBus(this.model.bus, "RELATIONAL_MODEL:RECORD_UPDATED", ({ detail }) => {
                this.props.info.onRecordChanged(detail.record, detail.changes);
            });
        }
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
];
