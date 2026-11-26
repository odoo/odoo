import { expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPoSEnvForSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

definePosModels();

test("showScanButton is only shown on the ticket screen in dynamic QR mode", async () => {
    const store = await setupPoSEnvForSelfOrder();
    store.addNewOrder();
    const comp = await mountWithCleanup(Navbar, {});
    comp.isBarcodeScannerSupported = () => true;

    store.router.currentScreen.set("TicketScreen");
    expect(comp.showScanButton).toBe(false);

    store.config.self_ordering_mode = "mobile";
    store.config.self_ordering_service_mode = "dynamic_qr";
    expect(comp.showScanButton).toBe(true);

    store.router.currentScreen.set("ProductScreen");
    expect(comp.showScanButton).toBe(false);
});
