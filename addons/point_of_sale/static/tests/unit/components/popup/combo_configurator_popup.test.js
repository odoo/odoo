import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
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

test("selected extra price matches the total shown in the popup", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(7);
    const comboConfigurator = await mountWithCleanup(ComboConfiguratorPopup, {
        props: { productTemplate: productTemplate, getPayload: () => {}, close: () => {} },
    });
    // Combo with 1 free unit, a base price of 200 and a second choice at + 50.
    const combo = productTemplate.combo_ids[1];
    const [freeChoice, paidChoice] = combo.combo_item_ids;

    comboConfigurator.state.qty[combo.id][paidChoice.id] = 2;

    // 1 unit beyond the free quota at 200, plus the 50 surcharge on both units.
    expect(comboConfigurator.getExtraQtyForItem(paidChoice)).toBe(1);
    expect(comboConfigurator.formattedSelectedExtraPrice(paidChoice)).toBe("$ 300");
    // The badge may not tell a different story than the total of the popup.
    expect(comboConfigurator.getExtraPriceForItem(paidChoice)).toBe(
        comboConfigurator.computeComboExtraPrice(combo)
    );
    // Nothing selected, nothing to pay for.
    expect(comboConfigurator.formattedSelectedExtraPrice(freeChoice)).toBe("");
});

test("no selected extra price when the choice has no free unit", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(7);
    const comboConfigurator = await mountWithCleanup(ComboConfiguratorPopup, {
        props: { productTemplate: productTemplate, getPayload: () => {}, close: () => {} },
    });
    // Combo without any free unit: formattedComboPrice already shows the full price.
    const combo = productTemplate.combo_ids[0];
    const comboItem = combo.combo_item_ids[1];

    comboConfigurator.state.qty[combo.id][comboItem.id] = 1;

    expect(comboConfigurator.formattedComboPrice(comboItem)).toBe("+ $ 135");
    expect(comboConfigurator.formattedSelectedExtraPrice(comboItem)).toBe("");
});
