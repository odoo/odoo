import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class BadgeStrategyPlugin extends Plugin {
    static id = "badgeStrategy";
    static dependencies = ["hybridFluidStrategy", "spacing"];
    resources = {
        is_responsive_element_predicates: this.preventResponsiveCTABadge.bind(this),
    };

    preventResponsiveCTABadge({ responsiveElement }) {
        // cta badge margin auto is handled fully by
        // the spacing_plugin, no need for it to become
        // a responsive element.
        if (responsiveElement.matches?.(".s_cta_badge")) {
            return false;
        }
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(BadgeStrategyPlugin.id, BadgeStrategyPlugin);
