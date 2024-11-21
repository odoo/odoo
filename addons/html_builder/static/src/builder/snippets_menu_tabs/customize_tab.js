import { Component } from "@odoo/owl";
import { WithSubEnv } from "../builder_helpers";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { WithSubEnv };
    static props = {
        selectedToolboxes: { type: Object },
    };
}
