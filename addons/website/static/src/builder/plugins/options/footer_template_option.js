import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";

export class FooterTemplateOption extends BaseOptionComponent {
    static template = "website.FooterTemplateOption";
    static props = { getTemplates: Function };

    setup() {
        super.setup();
        this.footerTemplates = useState(this.props.getTemplates());
    }
}

export class FooterTemplateChoice extends BaseOptionComponent {
    static template = "website.FooterTemplateChoice";
    static props = { title: String, view: String, varName: String, imgSrc: String };
}
