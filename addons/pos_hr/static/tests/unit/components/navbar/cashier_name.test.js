/* global Sha1 */

import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { CashierName } from "@point_of_sale/app/components/navbar/cashier_name/cashier_name";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("avatarAndCssClass", async () => {
    await setupPosEnv();
    const comp = await mountWithCleanup(CashierName, {});
    expect(comp.avatar).toBe("/web/image/hr.employee.public/2/avatar_128");
    expect(comp.cssClass).toMatchObject({ oe_status: true });
});
test("selectCashier", async () => {
    const store = await setupPosEnv();
    // Remove all employees except Administrator (id=2) and Employee1 (id=3)
    store.models["hr.employee"].forEach(
        (employee) => ![2, 3].includes(employee.id) && employee.delete()
    );
    const result = await store.selectCashier();
    expect(result.name).toBe("Employee1");
    expect(result.id).toBe(3);
    store.setCashier(result);
    const value = store.accessRight.loggedCashier;
    expect(value.name).toBe("Employee1");
    expect(value.id).toBe(3);
});
test("scanning a badge switches the cashier", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupPosEnv();
    const employee = store.models["hr.employee"].get(3);
    employee._barcode = Sha1.hash("041123");
    await mountWithCleanup(CashierName, {});

    await store.barcodeReader.scan("041123");
    expect(store.accessRight.loggedCashier.id).toBe(3);
});
