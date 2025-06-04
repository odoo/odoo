import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { onWillStart } from "@odoo/owl";
import { useCachedModel } from "@html_builder/core/cached_model_utils";

export class PortalOption extends BaseOptionComponent {
    static template = "website.PortalOption";
    static selector = ".o_portal_index_card > a";
    static editableOnly = false;
    static components = { BorderConfigurator };
    static groups = ["website.group_website_designer"];
}

export class PortalCardVisibilityOption extends BaseOptionComponent {
    static template = "website.PortalCardVisibilityOption";
    static selector = ".o_portal_wrap";
    static editableOnly = false;
    static reloadTarget = true;
    static groups = ["website.group_website_designer"];

    setup() {
        super.setup();
        this.cachedModel = useCachedModel();
        onWillStart(async () => {
            this.entries = await this.cachedModel.ormSearchRead(
                "portal.entry",
                ["&", ["is_config_card", "!=", true], ["category", "!=", "alert"]],
                ["name", "id"]
            );
        });
    }
}
