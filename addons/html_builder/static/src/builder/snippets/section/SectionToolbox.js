import { registry } from "@web/core/registry";
import { ElementToolboxContainer } from "../../components/ElementToolboxContainer";
import { Component } from "@odoo/owl";
import { LayoutOption } from "../../components/options/LayoutOption";
import { VisibilityOption } from "../../components/options/VisibilityOption";

class SectionToolbox extends Component {
    static template = "html_builder.SectionToolbox";
    static components = {
        ElementToolboxContainer,
        LayoutOption,
        VisibilityOption,
    };
}

registry.category("sidebar-element-toolbox").add("SectionToolbox", {
    ToolboxComponent: SectionToolbox,
    selector: "section",
});
