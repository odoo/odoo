import { Component } from "@odoo/owl";
import { ElementToolboxContainer } from "../../components/ElementToolboxContainer";
import { LayoutOption } from "../../components/options/LayoutOption";
import { VisibilityOption } from "../../components/options/VisibilityOption";

// TODO TO convert and remove

export class SectionToolbox extends Component {
    static template = "html_builder.SectionToolbox";
    static components = {
        ElementToolboxContainer,
        LayoutOption,
        VisibilityOption,
    };
}

// registry.category("sidebar-element-legacy-toolbox").add("SectionToolbox", {
//     ToolboxComponent: SectionToolbox,
//     selector: "section",
// });
