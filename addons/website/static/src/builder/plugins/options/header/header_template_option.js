import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderTemplateOption extends BaseOptionComponent {
    static template = "website.HeaderTemplateOption";
    static dependencies = ["headerOption"];

    setup() {
        super.setup();
        this.headerTemplates = useState(this.dependencies.headerOption.getHeaderTemplates());
    }

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}

Object.assign(HeaderTemplateOption, basicHeaderOptionSettings);

export class HeaderTemplateChoice extends BaseOptionComponent {
    static template = "website.HeaderTemplateChoice";
    static props = {
        title: String,
        views: Array,
        varName: String,
        imgSrc: String,
        id: String,
        menuShadowClass: String,
    };
}
