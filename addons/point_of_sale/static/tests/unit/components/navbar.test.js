import { test, expect } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("Backend button should not close the menu (closingMode='none')", async () => {
    const store = await setupPosEnv();

    patchWithCleanup(store, {
        async closePos() {},
    });

    await mountWithCleanup(Navbar);

    // 1. Open the burger menu dropdown
    await click(".status-buttons .o-dropdown.dropdown-toggle");
    await animationFrame();

    // Verify menu is open
    expect(".pos-burger-menu-items").toHaveCount(1);

    // 2. Find and click "Backend"
    const backendItem = [
        ...document.querySelectorAll(".pos-burger-menu-items .dropdown-item"),
    ].find((el) => el.textContent.includes("Backend"));
    expect(Boolean(backendItem)).toBe(true);

    await click(backendItem);
    await animationFrame();

    // 3. Verify the menu is STILL OPEN
    expect(".pos-burger-menu-items").toHaveCount(1);
});
