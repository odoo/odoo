import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { BaseVisibilityOption } from "./base_visibility_option";

export class TopMenuVisibilityOption extends BaseOptionComponent {
    static id = "top_menu_visibility_option";
    static template = "website.TopMenuVisibilityOption";
    static components = {
        BaseVisibilityOption,
    };
}

registry.category("builder-options").add(TopMenuVisibilityOption.id, TopMenuVisibilityOption);
