import { BaseOptionComponent } from "@html_builder/core/utils";

export class HeaderTemplateOption extends BaseOptionComponent {
    static template = "website.HeaderTemplateOption";
    static props = {};

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}
