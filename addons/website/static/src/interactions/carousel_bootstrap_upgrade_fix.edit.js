import { registry } from "@web/core/registry";
import { CarouselBootstrapUpgradeFix } from "@website/interactions/carousel_bootstrap_upgrade_fix";

const CarouselBootstrapUpgradeFixEdit = I => class extends I {
    // Suspend ride in edit mode.
    carouselOptions = {ride: false, pause: true};
};

registry
    .category("website.editable_active_elements_builders")
    .add("website.carousel_bootstrap_upgrade_fix", {
        Interaction: CarouselBootstrapUpgradeFix,
        mixin: CarouselBootstrapUpgradeFixEdit
    });
