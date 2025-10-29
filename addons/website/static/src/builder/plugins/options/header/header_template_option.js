import { BaseOptionComponent } from "@html_builder/core/utils";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderTemplateOption extends BaseOptionComponent {
    static template = "website.HeaderTemplateOption";

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}

Object.assign(HeaderTemplateOption, basicHeaderOptionSettings);
