import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("navbar.js", () => {
    test("showCreateProductButton", async () => {
        const store = await setupPosEnv();
        const comp = await mountWithCleanup(Navbar, {});
        const admin = store.models["hr.employee"].get(2);
        store.setCashier(admin);
        expect(comp.showCreateProductButton).toBe(true);
        const emp = store.models["hr.employee"].get(3);
        store.setCashier(emp);
        expect(comp.showCreateProductButton).toBe(false);
    });
});
