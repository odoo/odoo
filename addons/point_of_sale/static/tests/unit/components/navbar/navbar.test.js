import { test, expect } from "@odoo/hoot";
import { animationFrame, queryFirst } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

definePosModels();

test("the navbar is inert behind the login screen and the screen saver", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await mountWithCleanup(Navbar, {});
    store.navigate("ProductScreen", { orderUuid: order.uuid });
    await animationFrame();
    expect(".pos-topheader").not.toHaveAttribute("inert");

    store.navigate("LoginScreen");
    await animationFrame();
    expect(".pos-topheader").toHaveAttribute("inert");
    queryFirst(".orders-button").focus();
    expect(".orders-button").not.toBeFocused();

    store.navigate("SaverScreen");
    await animationFrame();
    expect(".pos-topheader").toHaveAttribute("inert");
});
