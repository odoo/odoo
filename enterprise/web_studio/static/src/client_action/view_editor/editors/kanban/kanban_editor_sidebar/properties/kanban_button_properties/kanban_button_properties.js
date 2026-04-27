import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { ClassAttribute } from "@web_studio/client_action/view_editor/interactive_editor/properties/class_attribute/class_attribute";
import { LimitGroupVisibility } from "@web_studio/client_action/view_editor/interactive_editor/properties/limit_group_visibility/limit_group_visibility";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";
import { ModifiersProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/modifiers/modifiers_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class KanbanButtonProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.KanbanButton";
    static props = {
        node: { type: Object },
    };
    static components = {
        ClassAttribute,
        LimitGroupVisibility,
        ModifiersProperties,
        Property,
        SidebarPropertiesToolbox,
    };
    setup() {
        this.editNodeAttributes = useEditNodeAttributes();
        // We don't want to display a in the sidebar.
        this.env.viewEditorModel.activeNode.humanName = _t("Button");
    }
    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }
}
