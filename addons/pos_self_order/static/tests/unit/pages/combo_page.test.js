import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ComboPage } from "@pos_self_order/app/pages/combo_page/combo_page";
import { setupSelfPosEnv, patchSession } from "../utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();
beforeEach(patchSession);

describe("combo_page", () => {
    test("onChoiceClicked", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;

        const comboProduct = models["product.template"].get(7);
        const comp = await mountWithCleanup(ComboPage, {
            props: { productTemplate: comboProduct },
        });

        // click selected choice
        comp.onChoiceClicked(0);
        expect(comp.state.showResume).toBeEmpty();
        expect(comp.currentChoiceState.displayAttributesOfItem).toBeEmpty();
        expect(comp.state.selectedChoiceIndex).toBe(0);

        // click next choice without seleting current
        const res = comp.onChoiceClicked(1);
        expect(res).toBeEmpty();
        expect(comp.state.selectedChoiceIndex).toBe(0);

        const item2 = models["product.combo.item"].get(2);
        comp.selectItem(item2);
        expect(comp.state.choices).toHaveLength(1);
        comp.onChoiceClicked(1);
        expect(comp.state.selectedChoiceIndex).toBe(1);
    });
});
