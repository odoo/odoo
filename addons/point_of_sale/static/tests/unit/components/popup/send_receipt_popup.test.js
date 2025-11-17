import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("generateTicketImage returns renderer output", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const comp = await mountWithCleanup(SendReceiptPopup, {
        props: { order, close: () => {} },
    });

    const result = await comp.generateTicketImage();
    expect(result).not.toBeEmpty();
});
