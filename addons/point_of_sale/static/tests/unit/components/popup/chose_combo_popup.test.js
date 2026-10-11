import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ChoseComboPopup } from "@point_of_sale/app/components/popups/chose_combo_popup/chose_combo_popup";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupPosEnv,
    createCombo,
    createComboTemplate,
    createComboItemProduct,
    createComboItemProducts,
} from "@point_of_sale/../tests/unit/utils";

definePosModels();

describe("chose_combo_popup.js", () => {
    test("allCombos", async () => {
        const store = await setupPosEnv();

        const addOrderlinesOfComboToCart = async (comboProduct) => {
            const comboChoices = comboProduct.combo_ids;
            const qtyTaken = {};
            for (const comboChoice of comboChoices) {
                const comboItems = comboChoice.combo_item_ids;
                const line = await store.addLineToCurrentOrder({
                    product_tmpl_id: comboItems[0].product_id.product_tmpl_id,
                    qty: comboChoice.is_upsell ? 1 : comboChoice.included_qty,
                });
                qtyTaken[comboChoice.id] = {
                    [line.uuid]: {
                        qty: line.qty,
                        combo_item: comboItems[0],
                    },
                };
                if (comboChoice.is_upsell) {
                    // Simulate that the upsell option has been chosen
                    qtyTaken[comboChoice.id].upsell = true;
                }
            }

            return qtyTaken;
        };

        const checkAllCombos = async (comboProduct, potentialCombos, isUpsell) => {
            const choseComboPopup = await mountWithCleanup(ChoseComboPopup, {
                props: {
                    potentialCombos,
                    close: () => {},
                    getPayload: () => {},
                },
            });
            let expectedLines = [];
            for (const comboChoice of comboProduct.combo_ids) {
                expectedLines.push({
                    name: comboChoice.combo_item_ids[0].product_id.display_name,
                    quantity: comboChoice.included_qty || 1,
                    upsell: false,
                    sequence: comboChoice.sequence,
                    id: comboChoice.id,
                });
                if (comboChoice.is_upsell && comboChoice.qty_max > 1) {
                    expectedLines.push({
                        name: comboChoice.name,
                        quantity: comboChoice.qty_max - 1,
                        upsell: true,
                        sequence: comboChoice.sequence,
                        id: comboChoice.id,
                    });
                }
            }
            expectedLines = expectedLines.sort((a, b) => {
                if (a.upsell !== b.upsell) {
                    return a.upsell ? 1 : -1;
                }
                if (a.sequence !== b.sequence) {
                    return a.sequence - b.sequence;
                }
                return a.id - b.id;
            });

            expect(choseComboPopup.allCombos).toHaveLength(1);
            expect(choseComboPopup.allCombos[0].product).toBe(comboProduct);
            expect(choseComboPopup.allCombos[0].lines).toEqual(expectedLines);
            expect(Boolean(choseComboPopup.allCombos[0].upsell)).toBe(isUpsell);
        };

        // Two combo choice, one is upsell, the other is not
        store.addNewOrder();
        const comboProduct_1 = store.models["product.template"].get(7);
        const qtyTaken_1 = await addOrderlinesOfComboToCart(comboProduct_1);
        const potentialCombos_1 = {
            product: comboProduct_1,
            combinations: [qtyTaken_1],
            totalComboPrice: 0,
            totalSplitedComboLinePrice: 0,
            upsell: true,
        };

        await checkAllCombos(comboProduct_1, [potentialCombos_1], true);

        // Two combo choices, none are upsell
        store.addNewOrder();
        const comboProduct_2 = store.models["product.template"].get(15);
        const qtyTaken_2 = await addOrderlinesOfComboToCart(comboProduct_2);
        const potentialCombos_2 = {
            product: comboProduct_2,
            combinations: [qtyTaken_2],
            totalComboPrice: 0,
            totalSplitedComboLinePrice: 0,
            upsell: false,
        };

        await checkAllCombos(comboProduct_2, [potentialCombos_2], false);

        // Two combo choices, both are upsell
        store.addNewOrder();
        const comboProduct_3 = store.models["product.template"].get(16);
        const qtyTaken_3 = await addOrderlinesOfComboToCart(comboProduct_3);
        const potentialCombos_3 = {
            product: comboProduct_3,
            combinations: [qtyTaken_3],
            totalComboPrice: 0,
            totalSplitedComboLinePrice: 0,
            upsell: true,
        };

        await checkAllCombos(comboProduct_3, [potentialCombos_3], true);
    });
});

test("popup renders with single applicable combo", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const product1 = createComboItemProduct(store, { name: "Test Product 1", price: 10 });
    const product2 = createComboItemProduct(store, { name: "Test Product 2", price: 15 });

    const combo = createCombo(store, {
        name: "Test Combo",
        items: [
            { productId: product1.variant, extraPrice: 0 },
            { productId: product2.variant, extraPrice: 0 },
        ],
        basePrice: 20,
        qtyFree: 1,
        qtyMax: 1,
        isUpsell: false,
    });

    createComboTemplate(store, { name: "Test Combo Template", combos: [combo] });

    await store.addLineToCurrentOrder({ product_tmpl_id: product1.template, qty: 1 });
    await store.addLineToCurrentOrder({ product_tmpl_id: product2.template, qty: 1 });

    const potentialCombos = [
        {
            product: store.models["product.template"]
                .getAll()
                .find((t) => t.name === "Test Combo Template"),
            combinations: [
                {
                    [combo.id]: {
                        line1: { qty: 1, combo_item: combo.combo_item_ids[0] },
                        line2: { qty: 1, combo_item: combo.combo_item_ids[1] },
                    },
                },
            ],
            totalComboPrice: 20,
            totalSplitedComboLinePrice: 25,
            upsell: false,
        },
    ];

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: { potentialCombos, close: () => {}, getPayload: () => {} },
    });

    expect(popup.allCombos).toHaveLength(1);
});

test("popup handles upsell combo correctly", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const products = createComboItemProducts(store, 4, { basePrice: 10 });

    const upsellCombo = createCombo(store, {
        name: "Upsell Combo",
        items: [
            { productId: products[1].variant, extraPrice: 0 },
            { productId: products[2].variant, extraPrice: 0 },
        ],
        basePrice: 20,
        qtyFree: 0,
        qtyMax: 2,
        isUpsell: true,
        sequence: 1,
    });

    createComboTemplate(store, { name: "Upsell Combo Template", combos: [upsellCombo] });

    const potentialCombos = [
        {
            product: store.models["product.template"]
                .getAll()
                .find((t) => t.name === "Upsell Combo Template"),
            combinations: [{ [upsellCombo.id]: { upsell: true } }],
            totalComboPrice: 20,
            totalSplitedComboLinePrice: 0,
            upsell: true,
        },
    ];

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: { potentialCombos, close: () => {}, getPayload: () => {} },
    });

    expect(popup.allCombos).toHaveLength(1);
    expect(Boolean(popup.allCombos[0].upsell)).toBe(true);
});

test("popup with applicable and upsell combos mixed", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const products = createComboItemProducts(store, 6, { basePrice: 10 });

    const applicableCombo = createCombo(store, {
        name: "Applicable Combo",
        items: [
            { productId: products[1].variant, extraPrice: 0 },
            { productId: products[2].variant, extraPrice: 0 },
        ],
        basePrice: 20,
        qtyFree: 1,
        qtyMax: 1,
        isUpsell: false,
    });

    const upsellCombo = createCombo(store, {
        name: "Upsell Combo",
        items: [
            { productId: products[3].variant, extraPrice: 0 },
            { productId: products[4].variant, extraPrice: 0 },
        ],
        basePrice: 25,
        qtyFree: 0,
        qtyMax: 2,
        isUpsell: true,
    });

    const comboTemplate = createComboTemplate(store, {
        name: "Mixed Combo Template",
        combos: [applicableCombo, upsellCombo],
    });

    const potentialCombos = [
        {
            product: comboTemplate.template,
            combinations: [
                {
                    [applicableCombo.id]: {
                        line1: { qty: 1, combo_item: applicableCombo.combo_item_ids[0] },
                        line2: { qty: 1, combo_item: applicableCombo.combo_item_ids[1] },
                    },
                },
            ],
            totalComboPrice: 20,
            totalSplitedComboLinePrice: 20,
            upsell: false,
        },
        {
            product: comboTemplate.template,
            combinations: [{ [upsellCombo.id]: { upsell: true } }],
            totalComboPrice: 25,
            totalSplitedComboLinePrice: 0,
            upsell: true,
        },
    ];

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: { potentialCombos, close: () => {}, getPayload: () => {} },
    });

    const upsellCombos = popup.allCombos.filter((c) => c.upsell);
    expect(upsellCombos).toHaveLength(1);
});

test("popup lines are correctly sorted by upsell and sequence", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const products = createComboItemProducts(store, 4, { basePrice: 10 });

    const combo = createCombo(store, {
        name: "Sorted Combo",
        items: [
            { productId: products[1].variant, extraPrice: 0 },
            { productId: products[2].variant, extraPrice: 0 },
            { productId: products[3].variant, extraPrice: 0 },
        ],
        basePrice: 30,
        qtyFree: 1,
        qtyMax: 2,
        isUpsell: false,
        sequence: 2,
    });

    const comboTemplate = createComboTemplate(store, {
        name: "Sorted Combo Template",
        combos: [combo],
    });

    const potentialCombos = [
        {
            product: comboTemplate.template,
            combinations: [
                {
                    [combo.id]: {
                        line1: { qty: 1, combo_item: combo.combo_item_ids[0] },
                        line2: { qty: 1, combo_item: combo.combo_item_ids[1] },
                        line3: { qty: 1, combo_item: combo.combo_item_ids[2] },
                    },
                },
            ],
            totalComboPrice: 30,
            totalSplitedComboLinePrice: 30,
            upsell: false,
        },
    ];

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: { potentialCombos, close: () => {}, getPayload: () => {} },
    });

    expect(popup.allCombos).toHaveLength(1);
});

test("popup confirm function calls getPayload correctly", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const products = createComboItemProducts(store, 2);

    const combo = createCombo(store, {
        name: "Confirm Test Combo",
        items: [
            { productId: products[1].variant, extraPrice: 0 },
            { productId: products[2].variant, extraPrice: 0 },
        ],
    });

    const comboTemplate = createComboTemplate(store, {
        name: "Confirm Test Template",
        combos: [combo],
    });

    let payloadReceived = null;
    let closeCalled = false;

    const potentialCombos = [
        {
            product: comboTemplate.template,
            combinations: [
                {
                    [combo.id]: {
                        line1: { qty: 1, combo_item: combo.combo_item_ids[0] },
                        line2: { qty: 1, combo_item: combo.combo_item_ids[1] },
                    },
                },
            ],
            totalComboPrice: 0,
            totalSplitedComboLinePrice: 0,
            upsell: false,
        },
    ];

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: {
            potentialCombos,
            close: () => {
                closeCalled = true;
            },
            getPayload: (payload) => {
                payloadReceived = payload;
            },
        },
    });

    const comboToConfirm = popup.allCombos[0];
    popup.confirm(comboToConfirm);

    expect(payloadReceived).toEqual(comboToConfirm);
    expect(closeCalled).toBe(true);
});
