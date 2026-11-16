import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const websiteSystrayRegistry = registry.category("website_systray");

patch(BurgerMenu.prototype, {
    setup() {
        super.setup();

        if (!websiteSystrayRegistry.contains("burger_menu")) {
            websiteSystrayRegistry.add(
                "burger_menu",
                registry.category("systray").get("burger_menu"),
                { sequence: 0 }
            );
        }
    },
});
