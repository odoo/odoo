import { BaseOptionComponent } from "@html_builder/core/utils";

export class HeaderElementsOption extends BaseOptionComponent {
    static template = "website.HeaderElementsOption";

    setup() {
        super.setup();
        this.customizeWebsite = this.env.editor.shared.customizeWebsite;
        const views = ["website.option_header_brand_logo", "website.option_header_brand_name"];
        this.customizeWebsite.loadConfigKey({ views });
    }

    get websiteLogoParams() {
        const views = this.customizeWebsite.getConfigKey("website.option_header_brand_name")
            ? ["website.option_header_brand_name"]
            : ["website.option_header_brand_logo"];
        return {
            views,
            resetViewArch: true,
        };
    }
}
