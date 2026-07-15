import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { onWillStart } from "@odoo/owl";

export class FooterTemplateOption extends BaseOptionComponent {
    static id = "footer_template_option";
    static template = "website.FooterTemplateOption";
    static dependencies = ["footerOption"];

    setup() {
        super.setup();
        onWillStart(async () => {
            this.footerTemplates = await this.dependencies.footerOption.getFooterTemplates();
        });
    }
}
registry.category("website-options").add(FooterTemplateOption.id, FooterTemplateOption);

export class FooterTemplateChoice extends BaseOptionComponent {
    static template = "website.FooterTemplateChoice";
    static props = { title: String, view: String, varName: String, imgSrc: String };
}
