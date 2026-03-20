import { Component, onWillStart, useState } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useAutofocus, useService } from "@web/core/utils/hooks";

export class FieldSelectorPopover extends Component {
    static template = "html_editor.FieldSelectorPopover";
    static components = { ModelFieldSelector };
    static props = {
        resModel: String,
        validate: Function,
        close: Function,
        path: { optional: true },
        label: { optional: true },
        disableLabel: { optional: true },
        followRelations: { optional: true },
        filter: { type: Function, optional: true },
    };
    static defaultProps = {
        path: false,
        label: false,
        followRelations: true,
        disableLabel: false,
    };

    setup() {
        useAutofocus();
        this.state = useState({
            path: this.props.path || "",
            label: this.props.label || "",
            modelName: this.props.resModel,
        });

        this.fieldService = useService("field");
        useHotkey("Enter", () => this.validate(), { bypassEditableProtection: true });
        useHotkey("Escape", () => this.props.close(), { bypassEditableProtection: true });

        onWillStart(async () => {
            this.state.modelName = this.props.resModel;
            if (this.state.path) {
                const fieldInfo = await this.getFieldInfo(this.state.path);
                this.fieldType = fieldInfo.type;
                this.state.fieldName = fieldInfo.string;
            }
        });
    }

    get resModel() {
        return this.props.resModel;
    }

    async getFieldInfo(path) {
        return (await this.fieldService.loadFieldInfo(this.resModel, path)).fieldDef;
    }

    onLabelInput(ev) {
        this.state.label = ev.target.value;
    }

    setPath(path, { fieldDef }) {
        this.state.path = path;
        this.state.fieldName = fieldDef?.string;
        this.fieldType = fieldDef?.type;

        if (fieldDef?.string) {
            this.state.label = fieldDef?.string;
        }
    }

    async validate() {
        const fieldInfo = await this.getFieldInfo(this.state.path);
        if (!fieldInfo) {
            return;
        }
        this.props.validate({
            path: this.state.path,
            label: this.state.label || "",
            fieldInfo,
            relation: fieldInfo.relation,
            relationName: fieldInfo.string,
        });
        this.props.close();
    }
}
