import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("PosSaleWarning: the warning of the selected customer is displayed", async () => {
    const store = await setupAndMountPosApp();
    store.models["res.partner"].get(3).sale_warn_msg = "Cannot afford our services";
    store.models["res.partner"].get(4).sale_warn_msg = "Highly infectious disease";

    await Utils.selectCustomer("Administrator");
    await waitFor(`.modal-header:contains("Warning for Administrator")`);
    expect(`.modal-body:contains("Cannot afford our services")`).toHaveCount(1);
    await contains(".modal-footer button").click();
    await Utils.checkSelectedCustomer("Administrator");

    await Utils.clickDisplayedProduct("TEST");
    expect(Utils.hasOrderline({ productName: "TEST", quantity: "1" })).toBe(true);

    await Utils.selectCustomer("User1");
    await waitFor(`.modal-header:contains("Warning for User1")`);
    expect(`.modal-body:contains("Highly infectious disease")`).toHaveCount(1);
    await contains(".modal-footer button").click();
    await Utils.checkSelectedCustomer("User1");

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();

    expect(store.getOrder().state).toBe("paid");
});

test("PosSaleWarning: the warning of the sold product is displayed", async () => {
    const store = await setupAndMountPosApp();
    store.models["product.template"].get(5).sale_line_warn_msg = "This product is discontinued";

    await Utils.clickDisplayedProduct("TEST");

    await waitFor(`.modal-header:contains("Warning for TEST")`);
    expect(`.modal-body:contains("This product is discontinued")`).toHaveCount(1);
    await contains(".modal-footer button").click();

    expect(store.getOrder().lines).toHaveLength(1);
});
