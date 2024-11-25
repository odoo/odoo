import { Component } from "@odoo/owl";
import { OptionsContainer } from "../components/OptionsContainer";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { OptionsContainer };
    static props = {
        currentOptionsContainers: { type: Array, optional: true },
    };
    static defaultProps = {
        currentOptionsContainers: [],
    };
}
