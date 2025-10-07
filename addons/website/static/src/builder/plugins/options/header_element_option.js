import { BaseOptionComponent } from "@html_builder/core/utils";

export class HeaderElementOption extends BaseOptionComponent {
    static template = "website.headerElementOption";
    static dependencies = ["customizeWebsite"];
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        this.customizeWebsite = this.dependencies.customizeWebsite;
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
