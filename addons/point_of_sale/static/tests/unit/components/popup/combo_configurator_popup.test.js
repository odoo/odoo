import { test, expect } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
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
    ).toEqual("+ $ 35");
    expect(
        comboConfigurator.formattedComboPrice(productTemplate.combo_ids[1].combo_item_ids[1])
    ).toEqual("+ $ 50");
});

test("combo choices sequence follows product pos_sequence and is_favorite", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(7);
    const combo = productTemplate.combo_ids[0];
    const items = combo.combo_item_ids;
    // Set first item's product pos_sequence to 20, and second item's product pos_sequence to 10
    items[0].product_id.product_tmpl_id.update({ pos_sequence: 20 });
    items[1].product_id.product_tmpl_id.update({ pos_sequence: 10 });

    await mountWithCleanup(ComboConfiguratorPopup, {
        props: { productTemplate: productTemplate, getPayload: () => {}, close: () => {} },
    });

    let productCards = queryAll(".combo-item .product-name");
    expect(productCards[0]).toHaveText(items[1].product_id.display_name);
    expect(productCards[1]).toHaveText(items[0].product_id.display_name);

    items[0].product_id.product_tmpl_id.update({ is_favorite: true });
    await mountWithCleanup(ComboConfiguratorPopup, {
        props: { productTemplate: productTemplate, getPayload: () => {}, close: () => {} },
    });

    productCards = queryAll(".combo-item .product-name");
    expect(productCards[0]).toHaveText(items[0].product_id.display_name);
    expect(productCards[1]).toHaveText(items[1].product_id.display_name);
});
