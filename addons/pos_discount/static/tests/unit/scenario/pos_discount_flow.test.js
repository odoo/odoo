import { expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { createTestProduct, setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as DiscountUiUtils from "@pos_discount/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...DiscountUiUtils };

definePosModels();

test("pos_discount_numpad: apply a fixed then a percentage global discount", async () => {
    const store = await setupAndMountPosApp({
        module_pos_restaurant: false,
        set_tip_after_payment: false,
        available_preset_ids: [],
    });
    store.config.discount_pc = 20;
    Utils.setFlatProductPrice(store, 25);

    await Utils.clickDisplayedProduct("TEST");
    await Utils.sendBufferKeys("4");

    const order = store.getOrder();
    order.setPricelist(store.models["product.pricelist"].get(2));
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].qty).toBe(4);
    expect(order.totalDue).toBe(100);

    // The popup starts on the configured percentage.
    await Utils.openDiscountPopup();
    expect(Utils.dialogTitle()).toBe("Discount");
    expect(Utils.numberPopupValue()).toBe("20 %");

    await Utils.sendBufferKeys("1", "0");
    await Utils.clickNumberPopupType("fixed");
    expect(Utils.selectedNumberPopupType()).toBe("fixed");
    expect(Utils.numberPopupValue()).toBe("$ 10.00");

    await press("Enter");
    expect(Utils.discountLines(order)).toHaveLength(1);
    expect(order.globalDiscountPc).toEqual({ value: 10, type: "fixed" });
    expect(order.totalDue).toBe(90);
    await advanceTime(150);
    expect(Utils.getOrderTotal()).toInclude("90");

    // Reopening the popup starts over from the configured percentage.
    await Utils.openDiscountPopup();
    expect(Utils.numberPopupValue()).toBe("20 %");

    await Utils.sendBufferKeys("2", "5");
    expect(Utils.selectedNumberPopupType()).toBe("percent");
    expect(Utils.numberPopupValue()).toBe("25 %");

    await press("Enter");
    expect(Utils.discountLines(order)).toHaveLength(1);
    expect(order.globalDiscountPc).toEqual({ value: 25, type: "percent" });
    expect(order.totalDue).toBe(75);
    await advanceTime(150);
    expect(Utils.getOrderTotal()).toInclude("75");

    await Utils.clickControlButton("Cancel Order");
    await Utils.confirmDialog();
    expect(store.getOrder().lines).toHaveLength(0);
});

test("PosDiscountServiceFeePresetSwitchTour: a global discount only reaches a fee based on the total after discount", async () => {
    const store = await setupAndMountPosApp({
        module_pos_restaurant: false,
        set_tip_after_payment: false,
    });
    store.config.discount_pc = 20;
    Utils.setFlatProductPrice(store, 100);

    const { variant: feeProduct } = createTestProduct(store, { name: "Service Fee", price: 0 });
    const makeFeePreset = (name, basedOn) =>
        store.models["pos.preset"].create({
            name,
            identification: "none",
            use_timing: false,
            attendance_ids: [],
            service_fee: true,
            service_fee_product_id: feeProduct,
            service_fee_type: "percent",
            service_fee_amount: 0.1,
            service_fee_based_on: basedOn,
        });
    const postDiscount = makeFeePreset("Percent 10 after discount", "post_discount");
    const preDiscount = makeFeePreset("Percent 10 before discount", "pre_discount");
    store.config.use_presets = true;
    store.config.default_preset_id = postDiscount;
    store.config.available_preset_ids = [postDiscount, preDiscount];
    await store.selectPreset(postDiscount);

    await Utils.clickDisplayedProduct("TEST");
    await advanceTime(150);

    const order = store.getOrder();
    order.setPricelist(store.models["product.pricelist"].get(2));
    const feeLines = () => order.serviceFeeLines;
    expect(feeLines()).toHaveLength(1);
    expect(feeLines()[0].price_unit).toBe(10); // 10% of 100.
    expect(order.totalDue).toBe(110);
    expect(Utils.hasOrderline({ productName: "Service Fee", price: "10.00" })).toBe(true);

    await Utils.openDiscountPopup();
    expect(Utils.numberPopupValue()).toBe("20 %");
    await press("Enter");
    await advanceTime(150);

    expect(Utils.discountLines(order)).toHaveLength(1);
    expect(Utils.discountLines(order)[0].price_unit).toBe(-20);
    expect(feeLines()).toHaveLength(1);
    expect(feeLines()[0].price_unit).toBe(8); // 10% of 100 - 20.
    expect(order.totalDue).toBe(88);
    expect(Utils.getOrderTotal()).toInclude("88");

    await Utils.clickControlButton("Percent 10 after discount");
    await advanceTime(150);

    expect(order.preset_id.id).toBe(preDiscount.id);
    expect(feeLines()).toHaveLength(1);
    expect(feeLines()[0].price_unit).toBe(10);
    expect(order.totalDue).toBe(90); // 100 - 20 + 10.
    expect(Utils.getOrderTotal()).toInclude("90");

    await Utils.clickControlButton("Percent 10 before discount");
    await advanceTime(150);

    expect(order.preset_id.id).toBe(postDiscount.id);
    expect(feeLines()).toHaveLength(1);
    expect(feeLines()[0].price_unit).toBe(8);
    expect(order.totalDue).toBe(88);

    await Utils.openDiscountPopup();
    await Utils.sendBufferKeys("1", "0", "0");
    expect(Utils.numberPopupValue()).toBe("100 %");
    await press("Enter");
    await advanceTime(150);

    expect(Utils.discountLines(order)[0].price_unit).toBe(-100);
    expect(feeLines()).toHaveLength(0);
    expect(order.totalDue).toBe(0);
    expect(Utils.doesNotHaveOrderline({ productName: "Service Fee" })).toBe(true);

    await Utils.clickControlButton("Percent 10 after discount");
    await advanceTime(150);

    expect(feeLines()).toHaveLength(1);
    expect(feeLines()[0].price_unit).toBe(10);
    expect(order.totalDue).toBe(10); // 100 - 100 + 10.
    expect(Utils.getOrderTotal()).toInclude("10.00");
});
