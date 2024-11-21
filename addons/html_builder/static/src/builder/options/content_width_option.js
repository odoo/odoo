import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../components/defaultComponents";

// TODO to import in html_builder

export class ContentWidthOption extends Component {
    static template = "html_builder.ContentWidthOption";
    static components = {
        ...defaultOptionComponents,
    };
}

registry.category("sidebar-element-option").add("ContentWidthOption", {
    OptionComponent: ContentWidthOption,
    selector: "section, .s_carousel .carousel-item, .s_carousel_intro_item",
    // TODO add exclude and target and remove applyTo in the template of ContentWidthOption
    // exclude: "[data-snippet] :not(.oe_structure) > [data-snippet]",
    // target: "> .container, > .container-fluid, > .o_container_small",
});
