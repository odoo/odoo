import { BaseOptionComponent } from "@html_builder/core/utils";
import { BaseVisibilityOption } from "./base_visibility_option";

export class BreadcrumbOption extends BaseOptionComponent {
    static template = "website.BreadcrumbOption";
    static components = { BaseVisibilityOption };
    static selector = ".o_page_breadcrumb";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}
