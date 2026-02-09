import { useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/utils";

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
