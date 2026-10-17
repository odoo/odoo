import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    createAttribute,
    createAttributeValue,
    setupPosEnv,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ComboConfiguratorPopup } from "@point_of_sale/app/components/popups/combo_configurator_popup/combo_configurator_popup";

definePosModels();

test("formattedComboPrice_contains_no_trailing_zeros", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(7);
    const comboConfigurator = await mountWithCleanup(ComboConfiguratorPopup, {
        props: { productTemplate: productTemplate, getPayload: () => {}, close: () => {} },
    });
    // check if no additional trailing zeros added from formatCurrency when the extra_price has decimals or not
    expect(
        comboConfigurator.formattedComboPrice(productTemplate.combo_ids[0].combo_item_ids[1])
    ).toEqual("+ $ 135");
    expect(
        comboConfigurator.formattedComboPrice(productTemplate.combo_ids[1].combo_item_ids[1])
    ).toEqual("+ $ 50");
});

test("selected extra price of combo choices", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(7);
    const comboConfigurator = await mountWithCleanup(ComboConfiguratorPopup, {
        props: { productTemplate: productTemplate, getPayload: () => {}, close: () => {} },
    });
    const extraPrice = (comboItem) =>
        comboConfigurator.formattedSelectedExtraPrice(
            comboItem,
            comboConfigurator.getExtraByItem()
        );
    const combo = productTemplate.combo_ids[1];
    const [freeChoice, paidChoice] = combo.combo_item_ids;
    combo.qty_max = 2;
    expect(comboConfigurator.includedText(combo)).toBe("1 included & $ 200 per extra unit");

    comboConfigurator.state.qty[combo.id][paidChoice.id] = 1;
    expect(extraPrice(paidChoice)).toBe("");
    comboConfigurator.state.qty[combo.id][paidChoice.id] = 2;
    expect(extraPrice(paidChoice)).toBe("$ 300");
    expect(extraPrice(freeChoice)).toBe("");

    const noFreeCombo = productTemplate.combo_ids[0];
    const noFreeChoice = noFreeCombo.combo_item_ids[1];
    comboConfigurator.state.qty[noFreeCombo.id][noFreeChoice.id] = 2;
    expect(extraPrice(noFreeChoice)).toBe("");

    combo.base_price = 0;
    expect(comboConfigurator.includedText(combo)).toBe("1 included");
});

test("selected combo items follow the quantities set in the popup", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(7);
    const combo = productTemplate.combo_ids[1];
    const [otherItem, comboItem] = combo.combo_item_ids;
    combo.qty_max = 3;
    const color = createAttribute(store, "Color", "radio");
    const [red, blue] = ["Red", "Blue"].map((name) => createAttributeValue(store, color, name));
    const order = store.addNewOrder();
    const [redLine, blueLine] = [red, blue].map((value) =>
        store.models["pos.order.line"].create({
            order_id: order,
            product_id: comboItem.product_id,
            qty: 1,
            attribute_value_ids: [value],
        })
    );
    const comboConfigurator = await mountWithCleanup(ComboConfiguratorPopup, {
        props: {
            productTemplate: productTemplate,
            values: {
                [combo.id]: {
                    [redLine.uuid]: { combo_item: comboItem, qty: 1 },
                    [blueLine.uuid]: { combo_item: comboItem, qty: 1 },
                },
            },
            getPayload: () => {},
            close: () => {},
        },
    });
    const selectedItems = () =>
        comboConfigurator
            .getSelectedComboItems()
            .map((items) =>
                items.map(({ configuration, qty }) => [configuration.attribute_value_ids, qty])
            );

    expect(selectedItems()).toEqual([[[[red.id], 1]], [[[blue.id], 1]]]);
    comboConfigurator.state.qty[combo.id][comboItem.id] = 3;
    expect(selectedItems()).toEqual([[[[red.id], 1]], [[[blue.id], 2]]]);
    comboConfigurator.state.qty[combo.id][comboItem.id] = 1;
    expect(selectedItems()).toEqual([[[[red.id], 1]], []]);

    comboConfigurator.state.qty[combo.id][comboItem.id] = 0;
    comboConfigurator.state.qty[combo.id][otherItem.id] = 1;
    comboConfigurator.state.configuration[`${otherItem.id}9`] = { attribute_value_ids: [red.id] };
    expect(comboConfigurator.getSelectedComboItems()[0][0].configuration).toBe(undefined);
});
