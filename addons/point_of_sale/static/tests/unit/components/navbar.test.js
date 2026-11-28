import { test, expect, animationFrame } from "@odoo/hoot";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("Navbar: Backend button triggers pos.closePos() from burger menu", async () => {
    const store = await setupAndMountPosApp();

    let closePosCalled = false;
    patchWithCleanup(store, {
        closePos() {
            closePosCalled = true;
        },
    });

    // Open POS burger menu
    await contains(".pos-topheader .fa-bars").click();
    await animationFrame();

    // Click Backend option in burger menu
    await contains(".pos-burger-menu-items .dropdown-item:contains('Backend')").click();
    await animationFrame();

    expect(closePosCalled).toBe(true);
});
