import { registry } from "@web/core/registry";
import { ElementToolboxContainer } from "../../components/ElementToolboxContainer";
import { Component } from "@odoo/owl";

class SectionToolbox extends Component {
    static template = "mysterious_egg.SectionToolbox";
    static components = {
        ElementToolboxContainer,
    };
}

registry.category("sidebar-element-toolbox").add("SectionToolbox", {
    ToolboxComponent: SectionToolbox,
    selector: "section",
});
