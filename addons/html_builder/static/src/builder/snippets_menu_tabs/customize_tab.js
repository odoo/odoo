import { Component } from "@odoo/owl";
import { Toolbar } from "@html_editor/main/toolbar/toolbar";
import { WithSubEnv } from "../builder_helpers";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { Toolbar, WithSubEnv };
    static props = {
        editor: { type: Object },
        selectedToolboxes: { type: Object },
    };
}
