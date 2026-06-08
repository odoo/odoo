import { test, expect } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { click } from "@mail/../tests/mail_test_helpers";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

definePosModels();

function buildComboPayloadFromValues(values) {
    const includedItems = [];
    for (const group of Object.values(values)) {
        for (const [key, comboValue] of Object.entries(group)) {
            if (key === "upsell") {
                continue;
            }
            includedItems.push({
                combo_item_id: comboValue.combo_item,
                qty: comboValue.qty,
                configuration: {
                    attribute_value_ids: comboValue.attribute_value_ids || [],
                    attribute_custom_values: {},
                },
            });
        }
    }
    return [includedItems, []];
}

test("test_convert_orderlines_to_combo: convert orderline to combo", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 2,
    });

    const comboTemplate = store.models["product.template"].get(17);
    const limited = store.getApplicableProductCombo("limited");
    const comboCandidate = limited.find((item) => item.productTmpl.id === comboTemplate.id);

    expect(comboCandidate.quantity).toBe(1);
    expect(comboCandidate.hasUpsell).toBe(false);

    const full = store.getApplicableProductCombo("full", comboTemplate);
    expect(full).toHaveLength(1);
    expect(full[0].combinationsQty).toBe(1);
    expect(full[0].totalComboPrice < full[0].totalSplitedComboLinePrice).toBe(true);
});

test("test_convert_orderlines_to_combo: convert orderlines to combo with upsell groups", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 1,
    });

    const comboTemplate = store.models["product.template"].get(7);
    const limited = store.getApplicableProductCombo("limited");
    const comboCandidate = limited.find((item) => item.productTmpl.id === comboTemplate.id);

    expect(comboCandidate.quantity).toBe(1);
    expect(comboCandidate.hasUpsell).toBe(true);

    const full = store.getApplicableProductCombo("full", comboTemplate);
    const containsUpsell = full[0].combinations.some((items) =>
        Object.values(items).some((comboValues) => comboValues.upsell)
    );
    expect(containsUpsell).toBe(true);
});

test("test_convert_orderlines_to_combo: do not suggest combo when all groups are upsell", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 2,
    });

    const allUpsellTemplate = store.models["product.template"].get(18);
    const limited = store.getApplicableProductCombo("limited");
    const candidate = limited.find((item) => item.productTmpl.id === allUpsellTemplate.id);
    expect(candidate).toBe(undefined);
});

test("test_convert_orderlines_to_combo: convert orderlines to combo with multiple quantities", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 4,
    });

    const comboTemplate = store.models["product.template"].get(17);
    const limited = store.getApplicableProductCombo("limited");
    const comboCandidate = limited.find((item) => item.productTmpl.id === comboTemplate.id);
    expect(comboCandidate.quantity).toBe(2);

    const full = store.getApplicableProductCombo("full", comboTemplate);
    expect(full).toHaveLength(1);
    expect(full[0].combinationsQty).toBe(2);
    expect(full[0].combinations).toHaveLength(2);
});

test("test_convert_orderlines_to_combo: convert orderlines to combo marks no upsell for regular combo", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 2,
    });

    const comboTemplate = store.models["product.template"].get(17);
    const full = store.getApplicableProductCombo("full", comboTemplate);
    const containsUpsell = full[0].combinations.some((items) =>
        Object.values(items).some((comboValues) => comboValues.upsell)
    );

    expect(containsUpsell).toBe(false);
});

test("test_convert_orderlines_to_combo: convert orderlines to combo no free item not applicable", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const comboTemplate = store.models["product.template"].get(7);
    comboTemplate.combo_ids.forEach((combo) => {
        combo.update({ is_upsell: true, qty_free: 0, qty_max: 5 });
    });

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 2,
    });

    const limited = store.getApplicableProductCombo("limited");
    const comboCandidate = limited.find((item) => item.productTmpl.id === comboTemplate.id);
    expect(comboCandidate).toBe(undefined);
});

test("test_convert_orderlines_to_combo: convert orderlines to combo creates combo parent and children", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 1,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 2,
    });

    const comboTemplate = store.models["product.template"].get(17);
    const combinations = store.getApplicableProductCombo("full", comboTemplate)[0].combinations;

    store.dialog.add = (_comp, props) => {
        props.getPayload(buildComboPayloadFromValues(props.values));
    };

    await store.createComboFromLines(comboTemplate, combinations);

    const comboParents = order.lines.filter(
        (line) => line.product_id.product_tmpl_id.id === comboTemplate.id && !line.combo_parent_id
    );
    expect(comboParents).toHaveLength(1);
    expect(comboParents[0].combo_line_ids.length > 0).toBe(true);

    const remainingRegularLines = order.lines.filter(
        (line) => [8, 10].includes(line.product_id.product_tmpl_id.id) && !line.combo_parent_id
    );
    expect(remainingRegularLines).toHaveLength(0);
});

test("test_convert_orderlines_to_combo: convert orderlines to combo apply first and keep remaining lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 4,
    });

    const comboTemplate = store.models["product.template"].get(17);
    const combinations = store.getApplicableProductCombo("full", comboTemplate)[0].combinations;

    let callCount = 0;
    store.dialog.add = (_comp, props, options) => {
        callCount++;
        if (callCount === 1) {
            props.getPayload(buildComboPayloadFromValues(props.values));
            return;
        }
        options.onClose();
    };

    await store.createComboFromLines(comboTemplate, combinations);

    const comboParents = order.lines.filter(
        (line) => line.product_id.product_tmpl_id.id === comboTemplate.id && !line.combo_parent_id
    );
    expect(comboParents).toHaveLength(1);

    const remainingRegularLines = order.lines.filter(
        (line) => [8, 10].includes(line.product_id.product_tmpl_id.id) && !line.combo_parent_id
    );
    expect(remainingRegularLines).toHaveLength(2);

    const qtyByTemplate = Object.fromEntries(
        remainingRegularLines.map((line) => [line.product_id.product_tmpl_id.id, line.qty])
    );
    expect(qtyByTemplate[8]).toBe(1);
    expect(qtyByTemplate[10]).toBe(2);
});

test("test_convert_orderlines_to_combo: convert orderlines to combo apply all combinations", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(10),
        qty: 4,
    });

    const comboTemplate = store.models["product.template"].get(17);
    const combinations = store.getApplicableProductCombo("full", comboTemplate)[0].combinations;

    store.dialog.add = (_comp, props) => {
        props.getPayload(buildComboPayloadFromValues(props.values));
    };

    await store.createComboFromLines(comboTemplate, combinations);

    const comboParents = order.lines.filter(
        (line) => line.product_id.product_tmpl_id.id === comboTemplate.id && !line.combo_parent_id
    );
    expect(comboParents).toHaveLength(2);

    const remainingRegularLines = order.lines.filter(
        (line) => [8, 10].includes(line.product_id.product_tmpl_id.id) && !line.combo_parent_id
    );
    expect(remainingRegularLines).toHaveLength(0);
});

test("test_convert_orderlines_to_combo_with_upsell: multiple combo suggestions and apply with configurator popup", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });

    await productScreen.addProductToOrder(store.models["product.template"].get(8));
    await productScreen.addProductToOrder(store.models["product.template"].get(10));
    await productScreen.addProductToOrder(store.models["product.template"].get(8));
    await productScreen.addProductToOrder(store.models["product.template"].get(10));

    await waitFor(".combo-proposition");

    const potentialCombos = store.getApplicableProductCombo("limited");
    expect(potentialCombos.length).toBe(2);

    await waitFor(".combo-proposition button");
    const button = document.querySelector(".combo-proposition button");
    const comboProposition = document.querySelector(".combo-proposition");
    const buttonText = button.textContent.trim();
    const comboPropositionText = comboProposition.textContent.replace(/\s+/g, " ").trim();
    expect(buttonText).toBe("Choose");
    expect(comboPropositionText).toMatch(/2 Product combo \+ Others/);
    await button.click();

    await waitFor(".chose-combo-popup");
    expect(document.querySelector(".section-title").textContent.trim()).toBe(
        "Chose a combo to apply"
    );

    const comboItems = document.querySelectorAll(".combo-item");
    expect(comboItems.length).toBe(2);

    const firstCombo = comboItems[0];
    const firstText = firstCombo.textContent.replace(/\s+/g, " ").trim();
    expect(firstText).toMatch(/Product combo/);
    expect(firstCombo.querySelector(".apply-combo-btn").textContent.trim()).toBe("Apply");
    expect(firstText).toMatch(/Add \$ ?113\.75/);
    expect(firstText).toMatch(/2 x Wood chair/);
    expect(firstText).toMatch(/2 x Wood desk/);

    const secondCombo = comboItems[1];
    const secondText = secondCombo.textContent.replace(/\s+/g, " ").trim();
    expect(secondCombo.querySelector(".apply-combo-btn").textContent.trim()).toBe("Choose");
    expect(secondText).toMatch(/Chairs Combo \(up to 9 more\)/);

    await click(".apply-combo-btn", { text: "Apply" });
});

test("test_convert_orderlines_to_combo_with_upsell: multiple combo suggestions shows choose button and verifies saved amount", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    store.models["product.combo"].getAll().forEach((combo) => {
        combo.base_price = 1;
    });
    store.models["product.template"].get(7).list_price = 1;
    store.models["product.template"].get(17).list_price = 1;
    store.models["product.template"].get(18).list_price = 1;
    store.models["product.product"].get(7).lst_price = 1;
    store.models["product.product"].get(17).lst_price = 1;
    store.models["product.product"].get(18).lst_price = 1;

    await productScreen.addProductToOrder(store.models["product.template"].get(8));
    await productScreen.addProductToOrder(store.models["product.template"].get(10));
    await productScreen.addProductToOrder(store.models["product.template"].get(8));
    await productScreen.addProductToOrder(store.models["product.template"].get(10));

    await waitFor(".combo-proposition");

    const potentialCombos = store.getApplicableProductCombo("limited");
    expect(potentialCombos.length).toBe(2);

    await waitFor(".combo-proposition button");
    const button = document.querySelector(".combo-proposition button");
    const comboProposition = document.querySelector(".combo-proposition");
    const buttonText = button.textContent.trim();
    const comboPropositionText = comboProposition.textContent.replace(/\s+/g, " ").trim();
    expect(buttonText).toBe("Choose");
    expect(comboPropositionText).toMatch(/2 Product combo \+ Others/);
    await button.click();

    await waitFor(".chose-combo-popup");
    expect(document.querySelector(".section-title").textContent.trim()).toBe(
        "Chose a combo to apply"
    );

    const comboItems = document.querySelectorAll(".combo-item");
    expect(comboItems.length).toBe(2);

    const firstCombo = comboItems[0];
    const firstText = firstCombo.textContent.replace(/\s+/g, " ").trim();
    expect(firstText).toMatch(/Product combo/);
    expect(firstCombo.querySelector(".apply-combo-btn").textContent.trim()).toBe("Apply");
    expect(firstText).toMatch(/Save \$ ?10\.00/);
    expect(firstText).toMatch(/2 x Wood chair/);
    expect(firstText).toMatch(/2 x Wood desk/);

    const secondCombo = comboItems[1];
    const secondText = secondCombo.textContent.replace(/\s+/g, " ").trim();
    expect(secondCombo.querySelector(".apply-combo-btn").textContent.trim()).toBe("Choose");
    expect(secondText).toMatch(/Chairs Combo \(up to 9 more\)/);
});
