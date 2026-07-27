import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    setupAndMountPosApp,
    createPosTestTax,
    createFiscalPosition,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("FiscalPositionNoTax: fiscal position maps tax to no tax", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const tax = createPosTestTax(store, {
        id: 100,
        name: "Tax 15%",
        amount: 15,
        priceInclude: true,
        fiscalPositionIds: [store.models["account.fiscal.position"].get(1)],
    });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 100;
    productTmpl.taxes_id = [tax];
    store.models["product.product"].get(5).lst_price = 100;

    const fpNoTax = store.models["account.fiscal.position"].get(2);
    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fpNoTax];
    await animationFrame();

    const order = store.getOrder();

    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines).toHaveLength(1);
    expect(Utils.getOrderTotal().includes("100.00")).toBe(true);

    await Utils.selectFiscalPosition("No tax fp");

    expect(Utils.getOrderTotal().includes("100.00")).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
});

test("FiscalPositionExcl: exclusive tax mapped to exclusive and inclusive", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const fpExclToExcl = createFiscalPosition(store, {
        id: 12,
        name: "Excl. to Excl.",
        taxMap: { 120: [121] },
    });
    const fpExclToIncl = createFiscalPosition(store, {
        id: 13,
        name: "Excl. to Incl.",
        taxMap: { 120: [122] },
    });

    const taxExcl20 = createPosTestTax(store, {
        id: 120,
        name: "Tax excl.20%",
        amount: 20,
        priceInclude: false,
    });
    createPosTestTax(store, {
        id: 121,
        name: "Tax excl.10%",
        amount: 10,
        priceInclude: false,
        fiscalPositionIds: [fpExclToExcl],
        originalTaxIds: [taxExcl20],
    });
    createPosTestTax(store, {
        id: 122,
        name: "Tax incl.10%",
        amount: 10,
        priceInclude: true,
        fiscalPositionIds: [fpExclToIncl],
        originalTaxIds: [taxExcl20],
    });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 100;
    productTmpl.taxes_id = [taxExcl20];
    store.models["product.product"].get(5).lst_price = 100;

    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fpExclToExcl, fpExclToIncl];
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");
    expect(Utils.getOrderTotal().includes("120.00")).toBe(true);

    await Utils.selectFiscalPosition("Excl. to Excl.");
    expect(Utils.getOrderTotal().includes("110.00")).toBe(true);

    await Utils.selectFiscalPosition("Excl. to Incl.");
    expect(Utils.getOrderTotal().includes("100.00")).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
});

test("FiscalPositionIncl: inclusive tax mapped to inclusive and exclusive", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const fpInclToIncl = createFiscalPosition(store, {
        id: 14,
        name: "Incl. to Incl.",
        taxMap: { 130: [131] },
    });
    const fpInclToExcl = createFiscalPosition(store, {
        id: 15,
        name: "Incl. to Excl.",
        taxMap: { 130: [132] },
    });

    const taxIncl20 = createPosTestTax(store, {
        id: 130,
        name: "Tax incl.20%",
        amount: 20,
        priceInclude: true,
    });
    createPosTestTax(store, {
        id: 131,
        name: "Tax incl.10%",
        amount: 10,
        priceInclude: true,
        fiscalPositionIds: [fpInclToIncl],
        originalTaxIds: [taxIncl20],
    });
    createPosTestTax(store, {
        id: 132,
        name: "Tax excl.10%",
        amount: 10,
        priceInclude: false,
        fiscalPositionIds: [fpInclToExcl],
        originalTaxIds: [taxIncl20],
    });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 100;
    productTmpl.taxes_id = [taxIncl20];
    store.models["product.product"].get(5).lst_price = 100;

    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fpInclToIncl, fpInclToExcl];
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");
    expect(Utils.getOrderTotal().includes("100.00")).toBe(true);

    await Utils.selectFiscalPosition("Incl. to Incl.");
    expect(Utils.getOrderTotal().includes("100.00")).toBe(true);

    await Utils.selectFiscalPosition("Incl. to Excl.");
    expect(Utils.getOrderTotal().includes("110.00")).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
});

test("pos_basic_order_03_tax_position: fiscal position changes tax on order", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 4.8;
    productTmpl.taxes_id = [store.models["account.tax"].get(1)];
    store.models["product.product"].get(5).lst_price = 4.8;

    createPosTestTax(store, { id: 200, name: "10%", amount: 10, priceInclude: false });
    const fp = createFiscalPosition(store, { id: 20, name: "FP-POS-2M", taxMap: { 1: [200] } });

    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fp];
    await animationFrame();

    const order = store.getOrder();

    await animationFrame();

    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines).toHaveLength(1);

    const totalBefore = Utils.getOrderTotal();
    expect(totalBefore).toInclude("5.52");

    await Utils.selectFiscalPosition("FP-POS-2M");

    const totalAfter = Utils.getOrderTotal();
    expect(totalAfter).toInclude("4.80");
});

test("test_tax_control_button_visiblity: fiscal position button hidden when disabled", async () => {
    await setupAndMountPosApp({ tax_regime_selection: false });

    await Utils.ensurePane("left");

    if (Utils.isMobile()) {
        await contains(".product-screen .mobile-more-button").click();
    } else {
        await contains(".product-screen .more-btn").click();
    }
    await animationFrame();

    const fpButton = document.querySelector(".o_fiscal_position_button");
    expect(fpButton).toBe(null);
});
