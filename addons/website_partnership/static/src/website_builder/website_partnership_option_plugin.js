import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { WebsitePartnersPage } from "./website_partnership_option";

class WebsitePartnershipPageOption extends Plugin {
    static id = "WebsitePartnershipPageOption";

    resources = {
        builder_options: [WebsitePartnersPage],
    };
}

registry
    .category("website-plugins")
    .add(WebsitePartnershipPageOption.id, WebsitePartnershipPageOption);
