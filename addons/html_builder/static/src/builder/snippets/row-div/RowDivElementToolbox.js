import { registry } from "@web/core/registry";
import { ElementToolboxContainer } from "../../components/ElementToolboxContainer";
import { Component } from "@odoo/owl";
import { BorderOption } from "../../components/options/BorderOption";

class RowDivElementToolbox extends Component {
    static template = "html_builder.RowDivElementToolbox";
    static components = {
        ElementToolboxContainer,
        BorderOption,
    };
}

registry.category("sidebar-element-toolbox").add("RowDivElementToolbox", {
    ToolboxComponent: RowDivElementToolbox,
    selector: "section .row > div",
});
