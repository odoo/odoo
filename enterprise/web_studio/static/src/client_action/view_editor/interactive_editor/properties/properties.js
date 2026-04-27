import { Component, useState, xml } from "@odoo/owl";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";

class DefaultProperties extends Component {
    static props = {
        node: { type: Object },
    };
    static template = xml`
        <SidebarPropertiesToolbox/>
    `;
    static components = { SidebarPropertiesToolbox };
}

export class Properties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties";
    static props = {
        propertiesComponents: { type: Object },
    };
    static components = { DefaultProperties };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
    }

    get iconClass() {
        // first check if the structure has a dedicated icon
        let icon =
            this.env.viewEditorModel.editorInfo.editor.Sidebar.viewStructures?.[this.nodeType]
                ?.class;
        if (!icon && this.nodeType === "field") {
            icon = `o_web_studio_field_${this.node.field.type}`;
        }
        return icon || `o_web_studio_field_${this.nodeType}`;
    }

    get node() {
        return this.viewEditorModel.activeNode;
    }

    get propertiesComponent() {
        return this.props.propertiesComponents[this.nodeType] || {};
    }

    get nodeType() {
        return this.node?.arch.tagName;
    }
}
