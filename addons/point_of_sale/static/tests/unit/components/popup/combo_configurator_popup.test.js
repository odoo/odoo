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
    ).toEqual("+ $ 35");
    expect(
        comboConfigurator.formattedComboPrice(productTemplate.combo_ids[1].combo_item_ids[1])
    ).toEqual("+ $ 50");
});
