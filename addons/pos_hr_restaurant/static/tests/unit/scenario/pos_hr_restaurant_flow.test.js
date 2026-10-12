import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as HrUiUtils from "@pos_hr/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...HrUiUtils };

definePosModels();

test("test_post_login_default_screen_is_tables: logging in lands on the floor screen", async () => {
    const store = await Utils.setupAndMountPosHrApp({ default_screen: "tables" });

    expect(Utils.loginScreenIsShown()).toBe(true);
    await Utils.login("Administrator", "1234");
    await waitFor(".floor-screen");
    expect(store.router.currentScreen()).toBe("FloorScreen");
});

test("test_post_login_default_screen_is_register: logging in lands on the product screen", async () => {
    const store = await Utils.setupAndMountPosHrApp({ default_screen: "register" });

    expect(Utils.loginScreenIsShown()).toBe(true);
    await Utils.login("Administrator", "1234");
    await waitFor(".product-screen");
    expect(store.router.currentScreen()).toBe("ProductScreen");
});
