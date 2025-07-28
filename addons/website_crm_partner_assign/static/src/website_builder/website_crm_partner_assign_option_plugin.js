import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { WebsiteCRMPartnersPage } from "./website_crm_partner_assign_option";

class WebsiteCRMPartnersPageOption extends Plugin {
    static id = "websiteCRMPartnersPageOption";
    resources = {
        builder_options: [WebsiteCRMPartnersPage],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteCRMPartnersPageOption.id, WebsiteCRMPartnersPageOption);
