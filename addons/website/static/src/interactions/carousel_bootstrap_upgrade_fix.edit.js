import { registry } from "@web/core/registry";
import { CarouselBootstrapUpgradeFix } from "@website/interactions/carousel_bootstrap_upgrade_fix";

export class CarouselBootstrapUpgradeFixEdit extends CarouselBootstrapUpgradeFix {
    // Suspend ride in edit mode.
    carouselOptions = {ride: false, pause: true};
}

registry
    .category("website.edit_active_elements")
    .add("website.carousel_bootstrap_upgrade_fix", CarouselBootstrapUpgradeFixEdit);
