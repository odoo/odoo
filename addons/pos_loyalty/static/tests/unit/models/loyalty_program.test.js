import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

describe("loyalty.program", () => {
    test("getEWalletGiftCardProgramType", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #2 - type = "ewallet"
        const program = models["loyalty.program"].get(2);

        const line = await addProductLineToOrder(store, order, {
            _e_wallet_program_id: program,
        });

        expect(line.getEWalletGiftCardProgramType()).toBe(`${program.program_type}`);
    });
});
