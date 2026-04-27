import { Component, useState } from "@odoo/owl";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { ExistingFields } from "@web_studio/client_action/view_editor/editors/components/view_fields";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { Properties } from "@web_studio/client_action/view_editor/interactive_editor/properties/properties";
import { FieldProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/field_properties/field_properties";
import { KanbanCoverProperties } from "@web_studio/client_action/view_editor/editors/kanban_legacy/kanban_editor_sidebar_legacy/properties/kanban_cover_properties/kanban_cover_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";
import { getFieldsInArch } from "@web_studio/client_action/utils";
import { _t } from "@web/core/l10n/translation";

class KanbanFieldProperties extends FieldProperties {
    onChangeAttribute(value, name) {
        if (name === "bold" && !value) {
            return this.editNodeAttributes({ [name]: "" });
        }
        return super.onChangeAttribute(...arguments);
    }
}

export class KanbanEditorSidebarLegacy extends Component {
    static template = "web_studio.ViewEditor.KanbanEditorSidebarLegacy";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
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
                component: KanbanFieldProperties,
                props: {
                    availableOptions: ["invisible", "string", "bold"],
                },
            },
            t: {
                component: KanbanCoverProperties,
            },
        };
    }

    get archInfo() {
        return this.viewEditorModel.controllerProps.archInfo;
    }

    get defaultGroupBy() {
        return {
            choices: fieldsToChoices(
                this.viewEditorModel.fields,
                this.viewEditorModel.GROUPABLE_TYPES,
                (field) => field.groupable
            ),
            required: false,
        };
    }

    get kanbanFieldsInArch() {
        // fields can be present in the xmlDoc to be preloaded, but not in
        // the actual template. Those must be present in the sidebar
        const kanbanXmlDoc = this.viewEditorModel.xmlDoc.querySelector("[t-name=kanban-box]");
        return getFieldsInArch(kanbanXmlDoc);
    }

    get defaultOrder() {
        if (this.archInfo.defaultOrder.length >= 1) {
            return this.archInfo.defaultOrder[0];
        } else {
            return { name: "", asc: true };
        }
    }

    get sortChoices() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            this.viewEditorModel.GROUPABLE_TYPES,
            (field) => field.sortable
        );
    }

    get orderChoices() {
        return [
            { value: "asc", label: _t("Ascending") },
            { value: "desc", label: _t("Descending") },
        ];
    }

    setSortBy(value) {
        this.onSortingChanged(value, this.defaultOrder.asc ? "asc" : "desc");
    }

    setOrder(value) {
        this.onSortingChanged(this.defaultOrder.name, value);
    }

    onSortingChanged(sortBy, order) {
        if (sortBy) {
            this.editAttribute(`${sortBy} ${order}`, "default_order");
        } else {
            this.editAttribute("", "default_order");
        }
    }

    editAttribute(value, name) {
        return this.editArchAttributes({ [name]: value });
    }

    editDefaultGroupBy(value) {
        this.editAttribute(value || "", "default_group_by");
    }
}
