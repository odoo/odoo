/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { ExistingFields } from "@web_studio/client_action/view_editor/view_structures/view_structures";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { Properties } from "@web_studio/client_action/view_editor/interactive_editor/properties/properties";
import { FieldProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/field_properties/field_properties";
import { KanbanCoverProperties } from "@web_studio/client_action/view_editor/editors/kanban/kanban_editor_sidebar/properties/kanban_cover_properties/kanban_cover_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";
import { getFieldsInArch } from "@web_studio/client_action/utils";

class KanbanFieldProperties extends FieldProperties {
    onChangeAttribute(value, name) {
        if (name === "bold" && !value) {
            return this.editNodeAttributes({ [name]: "" });
        }
        return super.onChangeAttribute(...arguments);
    }
}

export class KanbanEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.KanbanEditorSidebar";
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
            choices: fieldsToChoices(this.viewEditorModel.fields, (field) => {
                return field.store && this.viewEditorModel.GROUPABLE_TYPES.includes(field.type);
            }),
            required: false,
        };
    }

    get kanbanFieldsInArch() {
        // fields can be present in the xmlDoc to be preloaded, but not in
        // the actual template. Those must be present in the sidebar
        const kanbanXmlDoc = this.viewEditorModel.xmlDoc.querySelector("[t-name=kanban-box]")
        return getFieldsInArch(kanbanXmlDoc);
    }

    editAttribute(value, name) {
        return this.editArchAttributes({ [name]: value });
    }

    editDefaultGroupBy(value) {
        this.editAttribute(value || "", "default_group_by");
    }
}
