import { Component } from "@odoo/owl";
import { OptionsContainer } from "../../components/OptionsContainer";
import { BorderOption } from "../../options/BorderOption";

// TODO TO convert and remove
export class RowDivElementToolbox extends Component {
    static template = "html_builder.RowDivElementToolbox";
    static components = {
        OptionsContainer,
        BorderOption,
    };
}

// registry.category("sidebar-element-legacy-toolbox").add("RowDivElementToolbox", {
//     OptionComponent: RowDivElementToolbox,
//     selector: "section .row > div",
// });
