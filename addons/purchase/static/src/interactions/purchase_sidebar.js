import { Sidebar } from "@portal/interactions/sidebar";
import { registry } from "@web/core/registry";

export class PurchaseSidebar extends Sidebar {
    static selector = ".o_portal_purchase_sidebar";

    setup() {
        super.setup();
        this.spyWatched = document.querySelector("body[data-target='.navspy']");
    }

    start() {
        super.start();
        // Nav Menu ScrollSpy
        this.generateMenu({ "max-width": "200px" });
    }
}

registry
    .category("public.interactions")
    .add("purchase.purchase_sidebar", PurchaseSidebar);
