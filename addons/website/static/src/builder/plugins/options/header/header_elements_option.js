import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class HeaderElementsOption extends BaseOptionComponent {
    static id = "header_elements_option";
    static template = "website.HeaderElementsOption";
    static dependencies = ["customizeWebsite"];

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

registry.category("website-options").add(HeaderElementsOption.id, HeaderElementsOption);
