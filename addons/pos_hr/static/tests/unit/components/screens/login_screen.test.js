import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { destroyApp, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
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
    test("product scans are handled again once the login screen is gone", async () => {
        patchWithCleanup(session, { nomenclature_id: 1 });
        const store = await setupPosEnv();
        patchWithCleanup(store.router, { currentScreen: () => "LoginScreen" });
        const scanned = [];
        const notFound = [];
        store.barcodeReader.register({ product: (code) => scanned.push(code.base_code) });
        patchWithCleanup(store.barcodeReader, {
            showNotFoundNotification: (code) => notFound.push(code.code),
        });

        await mountWithCleanup(LoginScreen, {});
        destroyApp();
        await store.barcodeReader.scan("0123456789");
        expect(notFound).toEqual([]);
        expect(scanned).toEqual(["0123456789"]);
    });
});
