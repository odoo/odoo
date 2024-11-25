import { Component } from "@odoo/owl";
import { WithSubEnv } from "../builder_helpers";
import { ElementToolboxContainer } from "../components/ElementToolboxContainer";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { WithSubEnv, ElementToolboxContainer };
    static props = {
        selectedToolboxes: { type: Object },
    };
}
