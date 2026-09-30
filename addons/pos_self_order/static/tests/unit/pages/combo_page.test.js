import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ComboPage } from "@pos_self_order/app/pages/combo_page/combo_page";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("onChoiceClicked and selectItem", async () => {
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
    comp.onChoiceClicked(1);
    expect(comp.state.selectedChoiceIndex).toBe(0);

    const item2 = models["product.combo.item"].get(2);
    comp.selectItem(item2);
    expect(comp.state.choices).toHaveLength(1);
    comp.onChoiceClicked(1);
    expect(comp.state.selectedChoiceIndex).toBe(1);
});

test("getComboSelection", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const comboProduct = models["product.template"].get(7);
    const comp = await mountWithCleanup(ComboPage, {
        props: { productTemplate: comboProduct },
    });
    {
        const item = models["product.combo.item"].get(2);
        comp.selectItem(item);
        const selction = comp.getComboSelection();
        expect(selction).toHaveLength(1);
        expect(selction[0].combo_item_id.id).toBe(2);
        expect(selction[0].qty).toBe(1);
    }
    {
        const item = models["product.combo.item"].get(4);
        comp.selectItem(item);
        const selction = comp.getComboSelection();
        expect(selction).toHaveLength(2);
        expect(selction[1].combo_item_id.id).toBe(4);
        expect(selction[1].qty).toBe(1);
    }
});

test("isBackVisible", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const comboProduct = models["product.template"].get(7);
    const comp = await mountWithCleanup(ComboPage, {
        props: { productTemplate: comboProduct },
    });

    expect(comp.isBackVisible()).toBe(false);
    const item = models["product.combo.item"].get(2);
    comp.selectItem(item);
    comp.next();
    expect(comp.isBackVisible()).toBe(true);
});

test("isNextEnabled", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const comboProduct = models["product.template"].get(7);
    models["product.combo"].get(1).qty_free = 1;
    const comp = await mountWithCleanup(ComboPage, {
        props: { productTemplate: comboProduct },
    });

    expect(comp.isNextEnabled()).toBe(false);
    const item = models["product.combo.item"].get(2);
    comp.selectItem(item);
    expect(comp.isNextEnabled()).toBe(true);

    comp.next();
    expect(comp.isNextEnabled()).toBe(false);
});

test("attribute other than 'no_variant' and 'is_custom' in combo 'kiosk' mode is not allowed", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const comboProduct = models["product.template"].get(7);
    const item1 = models["product.combo.item"].get(2);
    const productWithCustomAttrvariant = models["product.product"].get(51);
    const item2 = models["product.combo.item"].create({
        combo_id: 2,
        product_id: productWithCustomAttrvariant.id,
    });
    const comp = await mountWithCleanup(ComboPage, {
        props: { productTemplate: comboProduct },
    });
    comp.selectItem(item1);
    expect(comp.isNextEnabled()).toBe(true);
    comp.next();
    comp.selectItem(item2);
    expect(comp.isNextEnabled()).toBe(true);
    expect(!!comp.hasAttribute(productWithCustomAttrvariant)).toBe(false);
});

test("'is_custom' is not configurable in combo 'kiosk' mode", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const comboProduct = models["product.template"].get(7);
    const item1 = models["product.combo.item"].get(2);
    const productWithCustomAttr = models["product.template"].get(51);
    productWithCustomAttr.attribute_line_ids = [productWithCustomAttr.attribute_line_ids[1]];
    const item2 = models["product.combo.item"].create({
        combo_id: 2,
        product_id: productWithCustomAttr.id,
    });
    const comp = await mountWithCleanup(ComboPage, {
        props: { productTemplate: comboProduct },
    });
    comp.selectItem(item1);
    expect(comp.isNextEnabled()).toBe(true);
    comp.next();
    comp.selectItem(item2);
    expect(comp.isNextEnabled()).toBe(true);
    expect(!!comp.hasAttribute(productWithCustomAttr)).toBe(false);
});

test("'is_custom' is configurable in combo 'mobile' mode", async () => {
    const store = await setupSelfPosEnv("mobile");
    const models = store.models;
    const comboProduct = models["product.template"].get(7);
    const item1 = models["product.combo.item"].get(2);
    const productWithCustomAttr = models["product.template"].get(51);
    productWithCustomAttr.attribute_line_ids = [productWithCustomAttr.attribute_line_ids[1]];
    const item2 = models["product.combo.item"].create({
        combo_id: 2,
        product_id: productWithCustomAttr.id,
    });

    const comp = await mountWithCleanup(ComboPage, {
        props: { productTemplate: comboProduct },
    });
    comp.selectItem(item1);
    expect(comp.isNextEnabled()).toBe(true);
    comp.next();
    comp.selectItem(item2);
    expect(comp.isNextEnabled()).toBe(false);
    expect(!!comp.hasAttribute(productWithCustomAttr)).toBe(true);
});
