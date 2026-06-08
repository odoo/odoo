import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ChoseComboPopup } from "@point_of_sale/app/components/popups/chose_combo_popup/chose_combo_popup";
import {
    setupPosEnv,
    createCombo,
    createComboTemplate,
    createComboItemProduct,
    createComboItemProducts,
    createCompleteComboSetup,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("allCombos", async () => {
    const store = await setupPosEnv();

    const addOrderlinesOfComboToCart = async (comboProduct) => {
        const comboChoices = comboProduct.combo_ids;
        const qtyTaken = {};
        for (const comboChoice of comboChoices) {
            const comboItems = comboChoice.combo_item_ids;
            const line = await store.addLineToCurrentOrder({
                product_tmpl_id: comboItems[0].product_id.product_tmpl_id,
                qty: comboChoice.is_upsell ? 1 : comboChoice.qty_free,
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

    const checkAllCombos = async (comboProduct, potentialCombos) => {
        const choseComboPopup = await mountWithCleanup(ChoseComboPopup, {
            props: {
                potentialCombos: potentialCombos,
                close: () => {},
                getPayload: () => {},
            },
        });
        let expectedLines = [];
        for (const comboChoice of comboProduct.combo_ids) {
            expectedLines.push({
                name: comboChoice.combo_item_ids[0].product_id.display_name,
                quantity: comboChoice.qty_free || 1,
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
        const combinationsExpected = potentialCombos.applicable.concat(potentialCombos.upsell);
        const expectedAllCombos = [
            {
                combinations: combinationsExpected[0].combinations,
                productTmpl: combinationsExpected[0].productTmpl,
                lines: expectedLines,
            },
        ];
        if (potentialCombos.upsell.length > 0) {
            expectedAllCombos[0].upsell = true;
        }
        expect(choseComboPopup.allCombos).toEqual(expectedAllCombos);
    };

    // Two combo choice, one is upsell, the other is not
    store.addNewOrder();
    const comboProduct_1 = store.models["product.template"].get(7);
    const qtyTaken_1 = await addOrderlinesOfComboToCart(comboProduct_1);
    const potentialCombos_1 = {
        applicable: [],
        upsell: [
            {
                productTmpl: comboProduct_1,
                combinations: [qtyTaken_1],
            },
        ],
    };

    await checkAllCombos(comboProduct_1, potentialCombos_1);

    // Two combo choices, none are upsell
    store.addNewOrder();
    const comboProduct_2 = store.models["product.template"].get(15);
    const qtyTaken_2 = await addOrderlinesOfComboToCart(comboProduct_2);
    const potentialCombos_2 = {
        applicable: [
            {
                productTmpl: comboProduct_2,
                combinations: [qtyTaken_2],
            },
        ],
        upsell: [],
    };

    await checkAllCombos(comboProduct_2, potentialCombos_2);

    // Two combo choices, both are upsell
    store.addNewOrder();
    const comboProduct_3 = store.models["product.template"].get(16);
    const qtyTaken_3 = await addOrderlinesOfComboToCart(comboProduct_3);
    const potentialCombos_3 = {
        applicable: [],
        upsell: [
            {
                productTmpl: comboProduct_3,
                combinations: [qtyTaken_3],
            },
        ],
    };

    await checkAllCombos(comboProduct_3, potentialCombos_3);
});

test("popup renders with single applicable combo", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const product1 = createComboItemProduct(store, {
        name: "Test Product 1",
        price: 10,
    });

    const product2 = createComboItemProduct(store, {
        name: "Test Product 2",
        price: 15,
    });

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

    const comboTemplate = createComboTemplate(store, {
        name: "Test Combo Template",
        combos: [combo],
    });

    await store.addLineToCurrentOrder({
        product_tmpl_id: product1.template,
        qty: 1,
    });

    await store.addLineToCurrentOrder({
        product_tmpl_id: product2.template,
        qty: 1,
    });

    const potentialCombos = {
        applicable: [
            {
                productTmpl: comboTemplate.template,
                combinations: [
                    {
                        [combo.id]: {
                            line1: { qty: 1, combo_item: combo.combo_item_ids[0] },
                            line2: { qty: 1, combo_item: combo.combo_item_ids[1] },
                        },
                    },
                ],
            },
        ],
        upsell: [],
    };

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: {
            potentialCombos,
            close: () => {},
            getPayload: () => {},
        },
    });

    expect(popup.allCombos).toHaveLength(1);
    expect(popup.allCombos[0].productTmpl.name).toBe("Test Combo Template");
    expect(popup.allCombos[0].lines).toHaveLength(2);
});

test("popup renders with multiple applicable combos", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const setup = createCompleteComboSetup(store, {
        templateId: 5600,
        templateName: "Multi Combo",
        numProducts: 9,
    });

    await store.addLineToCurrentOrder({
        product_tmpl_id: setup.products[1].template,
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: setup.products[2].template,
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: setup.products[3].template,
        qty: 1,
    });

    await store.addLineToCurrentOrder({
        product_tmpl_id: setup.products[4].template,
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: setup.products[5].template,
        qty: 1,
    });

    const potentialCombos = {
        applicable: [
            {
                productTmpl: setup.template,
                combinations: [
                    {
                        [setup.combos[0].id]: {
                            line1: { qty: 1, combo_item: setup.combos[0].combo_item_ids[0] },
                            line2: { qty: 1, combo_item: setup.combos[0].combo_item_ids[1] },
                            line3: { qty: 1, combo_item: setup.combos[0].combo_item_ids[2] },
                        },
                    },
                ],
            },
            {
                productTmpl: setup.template,
                combinations: [
                    {
                        [setup.combos[1].id]: {
                            line4: { qty: 1, combo_item: setup.combos[1].combo_item_ids[0] },
                            line5: { qty: 1, combo_item: setup.combos[1].combo_item_ids[1] },
                        },
                    },
                ],
            },
        ],
        upsell: [],
    };

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: {
            potentialCombos,
            close: () => {},
            getPayload: () => {},
        },
    });

    expect(popup.allCombos).toHaveLength(2);
});

test("popup handles upsell combo correctly", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const products = createComboItemProducts(store, 4, {
        basePrice: 10,
    });

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

    const comboTemplate = createComboTemplate(store, {
        name: "Upsell Combo Template",
        combos: [upsellCombo],
    });

    const potentialCombos = {
        applicable: [],
        upsell: [
            {
                productTmpl: comboTemplate.template,
                combinations: [
                    {
                        [upsellCombo.id]: {
                            upsell: true,
                        },
                    },
                ],
            },
        ],
    };

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: {
            potentialCombos,
            close: () => {},
            getPayload: () => {},
        },
    });

    expect(popup.allCombos).toHaveLength(1);
    expect(popup.allCombos[0].upsell).toBe(true);
});

test("popup with applicable and upsell combos mixed", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const products = createComboItemProducts(store, 6, {
        basePrice: 10,
    });
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

    const potentialCombos = {
        applicable: [
            {
                productTmpl: comboTemplate.template,
                combinations: [
                    {
                        [applicableCombo.id]: {
                            line1: { qty: 1, combo_item: applicableCombo.combo_item_ids[0] },
                            line2: { qty: 1, combo_item: applicableCombo.combo_item_ids[1] },
                        },
                    },
                ],
            },
        ],
        upsell: [
            {
                productTmpl: comboTemplate.template,
                combinations: [
                    {
                        [upsellCombo.id]: {
                            upsell: true,
                        },
                    },
                ],
            },
        ],
    };

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: {
            potentialCombos,
            close: () => {},
            getPayload: () => {},
        },
    });
    const upsellCombos = popup.allCombos.filter((c) => c.upsell);
    expect(upsellCombos).toHaveLength(1);
});

test("popup lines are correctly sorted by upsell and sequence", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const products = createComboItemProducts(store, 4, {
        basePrice: 10,
    });
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

    const potentialCombos = {
        applicable: [
            {
                productTmpl: comboTemplate.template,
                combinations: [
                    {
                        [combo.id]: {
                            line1: { qty: 1, combo_item: combo.combo_item_ids[0] },
                            line2: { qty: 1, combo_item: combo.combo_item_ids[1] },
                            line3: { qty: 1, combo_item: combo.combo_item_ids[2] },
                            upsell: true,
                        },
                    },
                ],
            },
        ],
        upsell: [],
    };

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: {
            potentialCombos,
            close: () => {},
            getPayload: () => {},
        },
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
    const getPayloadMock = (payload) => {
        payloadReceived = payload;
    };

    const potentialCombos = {
        applicable: [
            {
                productTmpl: comboTemplate.template,
                combinations: [
                    {
                        [combo.id]: {
                            line1: { qty: 1, combo_item: combo.combo_item_ids[0] },
                            line2: { qty: 1, combo_item: combo.combo_item_ids[1] },
                        },
                    },
                ],
            },
        ],
        upsell: [],
    };

    let closeCalled = false;
    const closeMock = () => {
        closeCalled = true;
    };

    const popup = await mountWithCleanup(ChoseComboPopup, {
        props: {
            potentialCombos,
            close: closeMock,
            getPayload: getPayloadMock,
        },
    });

    const comboToConfirm = popup.allCombos[0];
    popup.confirm(comboToConfirm);

    expect(payloadReceived).toEqual(comboToConfirm);
    expect(closeCalled).toBe(true);
});
