import { LimitGroupVisibility } from "@web_studio/client_action/view_editor/interactive_editor/properties/limit_group_visibility/limit_group_visibility";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";
import { Component, useState } from "@odoo/owl";

export class ViewStructureProperties extends Component {
    static components = { LimitGroupVisibility, SidebarPropertiesToolbox };
    static template = "web_studio.ViewStructureProperties";
    static props = {
        slots: { type: Object },
    };
    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
    }
}
