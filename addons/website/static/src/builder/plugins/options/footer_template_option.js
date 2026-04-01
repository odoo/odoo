import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";

export class FooterTemplateOption extends BaseOptionComponent {
    static template = "website.FooterTemplateOption";
    static dependencies = ["footerOption"];
    static selector = "#wrapwrap > footer";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];

    setup() {
        super.setup();
        this.footerTemplates = useState(this.dependencies.footerOption.getFooterTemplates());
    }
}

export class FooterTemplateChoice extends BaseOptionComponent {
    static template = "website.FooterTemplateChoice";
    static props = { title: String, view: String, varName: String, imgSrc: String };
}
