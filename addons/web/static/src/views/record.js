/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { useModel } from "@web/views/model";
import { RelationalModel } from "@web/views/relational_model";
const { Component, xml, onWillStart, onWillUpdateProps } = owl;

class _Record extends Component {
    setup() {
        const activeFields =
            this.props.info.activeFields ||
            Object.fromEntries(
                this.props.info.fieldNames.map((f) => [f, { attrs: {}, options: {}, domain: "[]" }])
            );

        this.model = useModel(RelationalModel, {
            resId: this.props.info.resId,
            resModel: this.props.info.resModel,
            fields: this.props.fields,
            viewMode: "form",
            rootType: "record",
            activeFields,
            mode: this.props.info.mode === "edit" ? "edit" : undefined,
            initialValues: this.props.info.initialValues,
        });
        onWillUpdateProps(async (nextProps) => {
            await this.model.load({
                resId: nextProps.info.resId,
                mode: nextProps.info.mode,
            });
        });
    }
}
_Record.template = xml`<t t-slot="default" record="model.root"/>`;

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
Record.template = xml`<_Record fields="fields" slots="props.slots" info="props" />`;
Record.components = { _Record };
Record.props = [
    "slots",
    "resModel",
    "fieldNames?",
    "activeFields?",
    "fields?",
    "resId?",
    "mode?",
    "initialValues?",
];
