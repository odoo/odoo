import { BaseOptionComponent } from "@html_builder/core/utils";
import { BaseVisibilityOption } from "./base_visibility_option";
import { registry } from "@web/core/registry";

export class BreadcrumbOption extends BaseOptionComponent {
    static id = "breadcrumb_option";
    static template = "website.BreadcrumbOption";
    static components = { BaseVisibilityOption };
}

registry.category("website-options").add(BreadcrumbOption.id, BreadcrumbOption);
