import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { unpatchSelf } from "@pos_self_order/app/services/data_service";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as ResUiUtils from "@pos_restaurant/../tests/unit/ui_utils";
import * as OpUiUtils from "@pos_online_payment/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...ResUiUtils, ...OpUiUtils };

definePosModels();

test("OnlinePaymentWithMultiTables: each table pays its own order online", async () => {
    unpatchSelf();
    const store = await setupAndMountPosApp({
        module_pos_restaurant: true,
        set_tip_after_payment: false,
        available_preset_ids: [],
    });
    Utils.addOnlinePaymentMethod(store, { only: true });
    Utils.setFlatProductPrice(store, 2.2);

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    const firstOrder = store.getOrder();
    expect(firstOrder.table_id.table_number).toBe(1);
    expect(firstOrder.totalDue).toBe(2.2);

    await Utils.clickPlanButton();
    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    const secondOrder = store.getOrder();
    expect(secondOrder.uuid).not.toBe(firstOrder.uuid);
    expect(secondOrder.table_id.table_number).toBe(4);
    expect(secondOrder.totalDue).toBe(4.4);
    expect(Utils.isValidateHighlighted()).toBe(true);

    await Utils.clickValidatePayment();
    await waitFor(".modal .o_qr_popup .qr-code-amount:contains('4.40')");

    expect(secondOrder.isSynced).toBe(true);
    const onlineLine = Utils.getOnlinePaymentLines(secondOrder)[0];
    expect(onlineLine.getAmount()).toBe(4.4);
    expect(onlineLine.getPaymentStatus()).toBe("waiting");
    expect(firstOrder.payment_ids).toHaveLength(0);
    expect(firstOrder.state).toBe("draft");
});
