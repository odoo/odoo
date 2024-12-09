import { registry } from "@web/core/registry";

// TODO to import in html_builder

registry.category("sidebar-element-option").add("ContentWidthOption", {
    template: "html_builder.ContentWidthOption",
    selector: "section, .s_carousel .carousel-item, .s_carousel_intro_item",
    // TODO add exclude and target and remove applyTo in the template of ContentWidthOption
    // exclude: "[data-snippet] :not(.oe_structure) > [data-snippet]",
    // target: "> .container, > .container-fluid, > .o_container_small",
});
