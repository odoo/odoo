import { Component, props, proxy, t } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { useAutofocus } from "@web/core/utils/hooks";

export class FieldSelectorPopover extends Component {
    static template = "html_editor.FieldSelectorPopover";
    props = props({
        resModel: t.string(),
        validate: t.function(),
        close: t.function(),
        path: t.any().optional(false),
        label: t.any().optional(false),
        disableLabel: t.any().optional(false),
        followRelation: t.any().optional(true),
        filter: t.function().optional(),
    });

    setup() {
        useAutofocus();
        this.state = proxy({
            path: this.props.path || "",
            label: this.props.label || "",
            modelName: this.props.resModel,
            fieldInfo: null,
        });

        this.fieldSelectorPopover = usePopover(ModelFieldSelectorPopover, {
            popoverClass: "o_popover_field_selector",
        });
        useHotkey("Enter", () => this.validate(), { bypassEditableProtection: true });
        useHotkey("Escape", () => this.props.close(), { bypassEditableProtection: true });
    }

    get resModel() {
        return this.props.resModel;
    }

    onLabelInput(ev) {
        this.state.label = ev.target.value;
    }

    get isValid() {
        // select a field, or just update the default
        return this.state.fieldInfo || this.state.path === this.props.path;
    }

    openFieldSelector(ev) {
        this.fieldSelectorPopover.open(ev.currentTarget, {
            close: () => this.fieldSelectorPopover.close(),
            filter: this.props.filter,
            followRelation: this.props.followRelation,
            isDebugMode: !!this.env.debug,
            path: this.state.path,
            readProperty: true,
            resModel: this.resModel,
            showDebugInput: false,
            showSearchInput: true,
            update: this.setPath.bind(this),
        });
    }

    setPath(path, fieldDef) {
        this.state.path = path;
        this.state.fieldName = fieldDef?.string;
        this.state.fieldInfo = fieldDef;

        if (fieldDef?.string) {
            this.state.label = fieldDef?.string;
        }
    }

    validate() {
        if (!this.state.path || !this.isValid) {
            return;
        }
        this.props.validate({
            path: this.state.path,
            label: this.state.label || "",
            fieldInfo: this.state.fieldInfo,
            relation: this.state.fieldInfo?.relation,
            relationName: this.state.fieldInfo?.string,
        });
        this.props.close();
    }
}
