import { BaseOptionComponent } from "@html_builder/core/utils";
import { BaseVisibilityOption } from "./base_visibility_option";

export class TopMenuVisibilityOption extends BaseOptionComponent {
    static template = "website.TopMenuVisibilityOption";
    static components = {
        BaseVisibilityOption,
    };
    static selector =
        "[data-main-object]:has(input.o_page_option_data[name='header_visible']) #wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}
