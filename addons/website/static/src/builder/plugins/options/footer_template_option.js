import { useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class FooterTemplateOption extends BaseOptionComponent {
    static id = "footer_template_option";
    static template = "website.FooterTemplateOption";
    static dependencies = ["footerOption"];

    setup() {
        super.setup();
        this.footerTemplates = useState(this.dependencies.footerOption.getFooterTemplates());
    }
}
registry.category("website-options").add(FooterTemplateOption.id, FooterTemplateOption);

export class FooterTemplateChoice extends BaseOptionComponent {
    static template = "website.FooterTemplateChoice";
    static props = { title: String, view: String, varName: String, imgSrc: String };
}
