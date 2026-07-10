import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { PairingPage } from "./pairing_index";

whenReady(async () => {
    await mountComponent(PairingPage, document.body);
});
