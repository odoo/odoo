import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { OwlybookView } from "./owlybook_view";

(async function startOwlybook() {
    await whenReady();
    await mountComponent(OwlybookView, document.body, {
        name: "Owlybook",
    });
})();
