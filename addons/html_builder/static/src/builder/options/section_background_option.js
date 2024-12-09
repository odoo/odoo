import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../components/defaultComponents";

// TODO to import in html_builder

export class SectionBackgroundOption extends Component {
    static template = "html_builder.SectionBackgroundOption";
    static components = { ...defaultOptionComponents };
    static props = {};
}

// todo: this is a naive implemenation. We should look at the current
// implementations of backgrounds options for all targets instead of just
// focusing on sections.
registry.category("sidebar-element-option").add("SectionBackgroundOption", {
    OptionComponent: SectionBackgroundOption,
    selector: "section",
});
