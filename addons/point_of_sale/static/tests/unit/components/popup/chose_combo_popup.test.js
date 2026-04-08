import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ChoseComboPopup } from "@point_of_sale/app/components/popups/chose_combo_popup/chose_combo_popup";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

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
