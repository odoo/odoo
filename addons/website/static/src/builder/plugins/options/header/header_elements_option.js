import { BaseOptionComponent } from "@html_builder/core/utils";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderElementsOption extends BaseOptionComponent {
    static template = "website.HeaderElementsOption";
<<<<<<< 189f0506f09249c5a7c2f7b7a5b02d9bd996014d
||||||| 4a1299e5439fa44eb73d613fec843f06dabaf895
    static dependencies = ["customizeWebsite"];
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
=======
    static dependencies = ["customizeWebsite"];
>>>>>>> 2bf23d432e9f7e85c8be1c9b1630f6a133c956c8

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

Object.assign(HeaderElementsOption, basicHeaderOptionSettings);
