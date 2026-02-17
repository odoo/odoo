import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
export class HeaderTemplateOption extends BaseOptionComponent {
    static id = "header_template_option";
    static template = "website.HeaderTemplateOption";

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}

registry.category("website-options").add(HeaderTemplateOption.id, HeaderTemplateOption);
