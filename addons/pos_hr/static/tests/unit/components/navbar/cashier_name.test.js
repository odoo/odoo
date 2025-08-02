import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { CashierName } from "@point_of_sale/app/components/navbar/cashier_name/cashier_name";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos_hr cashier_name.js", () => {
    test("avatarAndCssClass", async () => {
        await setupPosEnv();
        const comp = await mountWithCleanup(CashierName, {});
        expect(comp.avatar).toBe("/web/image/hr.employee.public/2/avatar_128");
        expect(comp.cssClass).toMatchObject({ oe_status: true });
    });
});
