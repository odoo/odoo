import { test, expect, describe } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { MockServer, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";
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
    test("cashier of an order loaded from another config is not selectable", async () => {
        const store = await setupPosEnv();
        const employeeId = MockServer.env["hr.employee"].create({ name: "New Employee" });
        const orderId = MockServer.env["pos.order"].create({ employee_id: employeeId, lines: [] });
        await store.data.loadServerOrders([["id", "=", orderId]]);
        expect(store.models["pos.order"].get(orderId).employee_id.id).toBe(employeeId);

        store.login = true;
        await mountWithCleanup(MainComponentsContainer);
        await mountWithCleanup(LoginScreen, {});
        await click(".select-cashier");
        await animationFrame();
        // The current cashier (Administrator) is not part of the selection
        expect(queryAllTexts(".selection-item")).toEqual(["A Little Guy", "Employee1"]);
    });
});
