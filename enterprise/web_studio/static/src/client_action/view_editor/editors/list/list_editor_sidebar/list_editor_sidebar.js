/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import {
    ExistingFields,
    NewFields,
} from "@web_studio/client_action/view_editor/editors/components/view_fields";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { Properties } from "@web_studio/client_action/view_editor/interactive_editor/properties/properties";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { FieldProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/field_properties/field_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";

class ListFieldNodeProperties extends FieldProperties {
    onChangeAttribute(value, name) {
        if (name !== "aggregate") {
            return super.onChangeAttribute(...arguments);
        }
        const activeNode = this.env.viewEditorModel.activeNode;
        const newAttrs = {
            avg: "",
            sum: "",
        };
        if (value && value !== "none") {
            const humanName = value === "sum" ? _t("Sum of %s") : _t("Average of %s");
            const fieldString = activeNode.attrs.string || activeNode.field.label;
            newAttrs[value] = sprintf(humanName, fieldString);
        }
        return this.editNodeAttributes(newAttrs);
    }
}

export class ListEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.ListEditorSidebar";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
        NewFields,
        ExistingFields,
        Property,
        Properties,
        SidebarViewToolbox,
    };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.editArchAttributes = useEditNodeAttributes({ isRoot: true });
        this.propertiesComponents = {
            field: {
                component: ListFieldNodeProperties,
                props: {
                    availableOptions: [
                        "invisible",
                        "required",
                        "readonly",
                        "string",
                        "help",
                        "optional",
                    ],
                },
            },
        };
    }

    get archInfo() {
        return this.viewEditorModel.controllerProps.archInfo;
    }

    get defaultOrder() {
        if (this.archInfo.defaultOrder.length >= 1) {
            return this.archInfo.defaultOrder[0];
        } else {
            return { name: "", asc: true };
        }
    }

    get editableChoices() {
        return [
            { value: "", label: _t("Open form view") },
            { value: "top", label: _t("Add record on top") },
            { value: "bottom", label: _t("Add record at the bottom") },
        ];
    }

    get sortChoices() {
        // only have stored fields that are present in arch
        const storeFieldsInArch = Object.fromEntries(
            Object.values(this.archInfo.fieldNodes).map((field) => [
                field.name,
                this.viewEditorModel.fields[field.name],
            ])
        );
        return fieldsToChoices(
            storeFieldsInArch,
            null,
            (field) => !["one2many", "many2many", "binary"].includes(field.type) && field.store
        );
    }

    get orderChoices() {
        return [
            { value: "asc", label: _t("Ascending") },
            { value: "desc", label: _t("Descending") },
        ];
    }

    get defaultGroupbyChoices() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            this.viewEditorModel.GROUPABLE_TYPES,
            (field) => field.groupable
        );
    }

    setSortBy(value) {
        this.onSortingChanged(value, this.defaultOrder.asc ? "asc" : "desc");
    }

    setOrder(value) {
        this.onSortingChanged(this.defaultOrder.name, value);
    }

    onSortingChanged(sortBy, order) {
        if (sortBy) {
            this.onAttributeChanged(`${sortBy} ${order}`, "default_order");
        } else {
            this.onAttributeChanged("", "default_order");
        }
    }

    onAttributeChanged(value, name) {
        return this.editArchAttributes({ [name]: value });
    }
}
