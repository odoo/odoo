import { BaseOptionComponent } from "@html_builder/core/base_option_component";
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
                [
                    "&",
                    ["category", "!=", "alert"],
                    "|",
                    ["is_config_card", "!=", true],
                    ["placeholder_count", "!=", false],
                ],
                ["name", "id"]
            );
        });
    }
}

registry.category("website-options").add(PortalCardVisibilityOption.id, PortalCardVisibilityOption);
