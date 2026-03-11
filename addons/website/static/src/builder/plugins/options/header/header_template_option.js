import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";

export class HeaderTemplateOption extends BaseOptionComponent {
    static id = "header_template_option";
    static template = "website.HeaderTemplateOption";
    static dependencies = ["headerOption"];

    setup() {
        super.setup();
        this.headerTemplates = this.dependencies.headerOption.getHeaderTemplates();
    }

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}

registry.category("website-options").add(HeaderTemplateOption.id, HeaderTemplateOption);

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
