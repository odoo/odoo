import { HEADER_ELEMENTS } from "@website/builder/plugins/options/header/header_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { after } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class ShowEmptyOption extends BaseOptionComponent {
    static template = "website_sale.ShowEmptyOption";
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class WebsiteSaleShowEmptyOptionPlugin extends Plugin {
    static id = "showEmptyOption";
    resources = {
        builder_options: [
            withSequence(after(HEADER_ELEMENTS), ShowEmptyOption),
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteSaleShowEmptyOptionPlugin.id, WebsiteSaleShowEmptyOptionPlugin);
