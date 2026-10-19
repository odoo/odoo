import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos_login_screen.js", () => {
    test("openRegister", async () => {
        const store = await setupPosEnv();
        const comp = await mountWithCleanup(LoginScreen, {});
        comp.openRegister();
        expect(store.login).toBe(true);
    });
    test("backBtnName", async () => {
        const store = await setupPosEnv();
        store.login = true;
        const comp = await mountWithCleanup(LoginScreen, {});
        expect(comp.backBtnName).toBe("Discard");
    });
});
