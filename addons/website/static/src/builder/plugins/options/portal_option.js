import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useCachedModel } from "@html_builder/core/cached_model_utils";
import { registry } from "@web/core/registry";

export class PortalCardVisibilityOption extends BaseOptionComponent {
    static id = "portal_card_visibility_option";
    static template = "website.PortalCardVisibilityOption";

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

registry.category("website-options").add(PortalCardVisibilityOption.id, PortalCardVisibilityOption);
