import { CarouselBootstrapUpgradeFix } from "@website/interactions/carousel/carousel_bootstrap_upgrade_fix";
import { registry } from "@web/core/registry";
import { withHistory } from "@website/core/website_edit_service";

const CarouselBootstrapUpgradeFixEdit = (I) =>
    class extends I {
        // Suspend ride in edit mode.
        carouselOptions = { ride: false, pause: true, keyboard: false };

        setup() {
            super.setup();
            this.dynamicContent = withHistory(this.dynamicContent);
        }
    };

registry.category("public.interactions.edit").add("website.carousel_bootstrap_upgrade_fix", {
    Interaction: CarouselBootstrapUpgradeFix,
    mixin: CarouselBootstrapUpgradeFixEdit,
});
