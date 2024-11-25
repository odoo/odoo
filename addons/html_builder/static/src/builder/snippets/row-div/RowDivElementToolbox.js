import { Component } from "@odoo/owl";
import { ElementToolboxContainer } from "../../components/ElementToolboxContainer";
import { BorderOption } from "../../components/options/BorderOption";

// TODO TO convert and remove
export class RowDivElementToolbox extends Component {
    static template = "html_builder.RowDivElementToolbox";
    static components = {
        ElementToolboxContainer,
        BorderOption,
    };
}

// registry.category("sidebar-element-legacy-toolbox").add("RowDivElementToolbox", {
//     ToolboxComponent: RowDivElementToolbox,
//     selector: "section .row > div",
// });
