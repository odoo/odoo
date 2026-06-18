import { useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { useAutofocus } from "@web/core/utils/hooks";

class EditorModelFieldSelectorPopover extends ModelFieldSelectorPopover {
    // When clicking on a field of which we can follow relation, we return the
    // display name by default.
    async selectFieldDisplayname(fieldDef) {
        const { modelsInfo } = await this.keepLast.add(
            this.fieldService.loadPath(
                fieldDef.is_property ? fieldDef.relation : this.state.page.resModel,
                `${fieldDef.name}.*`
            )
        );
        const { fieldDefs } = modelsInfo.at(-1);
        const fieldName = `${fieldDef.name}.display_name`;
        const fieldData = fieldDefs.display_name;
        this.state.label = fieldDef.string;
        return [fieldName, fieldData];
    }

    async selectField(field) {
        if (field.type === "properties") {
            return this.followRelation(field);
        }
        this.state.isFollowable = this.canFollowRelationFor(field);
        const [fieldName, fieldData] = this.state.isFollowable
            ? await this.selectFieldDisplayname(field)
            : [field.name, field];
        this.keepLast.add(Promise.resolve());
        this.state.page.selectedName = fieldName;
        if (this.state.isFollowable) {
            this.props.update(this.state.page.path, fieldData, this.state.label);
        } else {
            this.props.update(this.state.page.path, fieldData);
        }
        this.props.close(true);
    }
}

export class FieldSelectorPopover extends Component {
    static template = "html_editor.FieldSelectorPopover";
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
            fieldInfo: null,
        });

        this.fieldSelectorPopover = usePopover(EditorModelFieldSelectorPopover, {
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
            followRelations: this.props.followRelations,
            isDebugMode: !!this.env.debug,
            path: this.state.path,
            readProperty: true,
            resModel: this.resModel,
            showDebugInput: false,
            showSearchInput: true,
            update: this.setPath.bind(this),
        });
    }

    setPath(path, fieldDef, forcedLabel = null) {
        this.state.path = path;
        this.state.fieldName = forcedLabel || fieldDef?.string;
        this.state.fieldInfo = fieldDef;

        if (forcedLabel) {
            this.state.label = forcedLabel;
        } else if (fieldDef?.string) {
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
