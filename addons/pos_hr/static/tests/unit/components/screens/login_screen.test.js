/* global Sha1 */

import { test, expect, describe } from "@odoo/hoot";
import { click, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
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
    test("Enter typed in the cashier selection does not open it again", async () => {
        const store = await setupPosEnv();
        for (const employee of store.models["hr.employee"].getAll()) {
            employee._pin = Sha1.hash("1234");
        }
        store.login = true;
        await mountWithCleanup(MainComponentsContainer);
        const comp = await mountWithCleanup(LoginScreen, {});
        comp.state.pin = "1234";
        // The screen listens to keypress, which Hoot's helpers no longer dispatch.
        window.dispatchEvent(new KeyboardEvent("keypress", { key: "Enter" }));
        await animationFrame();
        expect(".modal").toHaveCount(1);

        queryFirst(".modal .selection-item").dispatchEvent(
            new KeyboardEvent("keypress", { key: "Enter", bubbles: true })
        );
        await animationFrame();
        expect(".modal").toHaveCount(1);
    });
});
