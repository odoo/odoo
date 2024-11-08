import { Component, useSubEnv } from "@odoo/owl";
import { Toolbar } from "@html_editor/main/toolbar/toolbar";

export class CustomizeTab extends Component {
    static template = "mysterious_egg.CustomizeTab";
    static components = { Toolbar };
    static props = {
        editor: { type: Object },
        selectedToolboxes: { type: Object },
    };
    setup() {
        useSubEnv({ editor: this.props.editor });
    }
}
