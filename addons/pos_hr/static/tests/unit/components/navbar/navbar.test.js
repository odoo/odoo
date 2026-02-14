import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("showCreateProductButtonWithAdmin", async () => {
    const store = await setupPosEnv();
    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    const comp = await mountWithCleanup(Navbar, {});
    expect(comp.showCreateProductButton).toBe(true);
});

test("showCreateProductButtonWithNonAdmin", async () => {
    const store = await setupPosEnv();
    const emp = store.models["hr.employee"].get(3);
    store.setCashier(emp);
    const comp = await mountWithCleanup(Navbar, {});
    expect(comp.showCreateProductButton).toBe(false);
});
