import { CarouselBootstrapUpgradeFix } from "@website/interactions/carousel/carousel_bootstrap_upgrade_fix";
import { registry } from "@web/core/registry";

const CarouselBootstrapUpgradeFixEdit = I => class extends I {
    // Suspend ride in edit mode.
    carouselOptions = { ride: false, pause: true };
};

registry
    .category("public.interactions.edit")
    .add("website.carousel_bootstrap_upgrade_fix", {
        Interaction: CarouselBootstrapUpgradeFix,
        mixin: CarouselBootstrapUpgradeFixEdit,
    });
