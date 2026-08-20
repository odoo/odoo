import { uuidv4 } from "@point_of_sale/utils";
import {
    assignDialogTestEnv,
    contains,
    getService,
    makeTestApp,
    mountWithCleanup,
    patchWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { animationFrame, tick, waitFor, waitUntil } from "@odoo/hoot-dom";
import { mountPosApp } from "@point_of_sale/../tests/unit/ui_utils";
import { expect } from "@odoo/hoot";
import { MainComponentsContainer } from "@web/core/main_components_container";

const { DateTime } = luxon;

export const setupPosEnv = async () => {
    // Do not change these variables, they are in accordance with the demo data
    odoo.pos_session_id = 1;
    odoo.pos_config_id = 1;
    odoo.from_backend = 0;
    odoo.access_token = uuidv4(); // Avoid indexedDB conflicts
    odoo.info = {
        db: `pos-${uuidv4()}`, // Avoid indexedDB conflicts
        isEnterprise: true,
    };

    assignDialogTestEnv();
    await makeTestApp();
    onRpc("/css", () => "");
    const store = getService("pos");
    store.setCashier(store.user);
    patchWithCleanup(store.router, {
        navigate(routeName, routeParams = {}) {
            this.currentScreen.set(routeName);
            this.currentScreenParams.set(routeParams);
        },
    });
    return store;
};

export const getFilledOrder = async (store, data = {}) => {
    const order = store.addNewOrder(data);
    const product1 = store.models["product.template"].get(5);
    const product2 = store.models["product.template"].get(6);
    const date = DateTime.now();
    order.write_date = date;
    order.create_date = date;

    await store.addLineToOrder(
        {
            product_tmpl_id: product1,
            qty: 3,
            write_date: date,
            create_date: date,
        },
        order
    );
    await store.addLineToOrder(
        {
            product_tmpl_id: product2,
            qty: 2,
            write_date: date,
            create_date: date,
        },
        order
    );
    store.addPendingOrder([order.id]);
    return order;
};

export const makeOrder = (store, overrides = {}) => {
    const order = store.createNewOrder();
    Object.assign(order, {
        state: "draft",
        date_order: DateTime.now(),
        pos_reference: "Order 00001",
        getScreenData: () => ({ name: "ProductScreen" }),
        ...overrides,
    });
    return order;
};

export async function waitUntilOrdersSynced(store, options) {
    await waitUntil(() => !store.syncingOrders.size, options);
    await tick();
}

export const mountPosDialog = async (component, props) => {
    const dialog = getService("dialog");
    const root = await mountWithCleanup(MainComponentsContainer);
    const getComponentInstance = (root) => {
        const flattenedChildren = (comp, acc = {}) => {
            for (const child of Object.values(comp.children)) {
                acc[child.componentName] = child;
                flattenedChildren(child, acc);
            }
            return acc;
        };
        const components = flattenedChildren(root);
        return components[component.name];
    };
    dialog.add(component, props);

    const dialogNode = await waitUntil(() => getComponentInstance(root.__owl__));
    return dialogNode.component;
};

export const expectFormattedPrice = (value, expected) => {
    expect(value).toBe(expected.replaceAll(" ", "\u00a0"));
};

export const dialogActions = async (action, steps = []) => {
    // Launch the action in a promise to be able to await the end of the steps
    await mountWithCleanup(MainComponentsContainer);
    const promise = new Promise((resolve) => {
        const call = async (fn) => {
            const result = await fn();
            resolve(result);
        };
        call(action);
    });

    // Wait for the dialog to be mounted
    await waitFor(".o_dialog");

    // Execute the steps one by one
    for (const step of steps) {
        await step();
        await animationFrame();
    }

    // Return the result of the action
    return await promise;
};

export const createPaymentLine = (store, order, paymentMethod, data = {}) =>
    store.models["pos.payment"].create({
        amount: 10,
        payment_method_id: paymentMethod.id,
        pos_order_id: order.id,
        write_date: DateTime.now(),
        create_date: DateTime.now(),
        ...data,
    });

export const activateMountingDialogs = async (env) => {
    await mountWithCleanup(MainComponentsContainer, { env });
};

export const normalizeFunctionsInObject = (obj) =>
    Object.fromEntries(
        Object.entries(obj).map(([key, value]) => [
            key,
            typeof value === "function" ? "function" : value,
        ])
    );

export async function setupAndMountPosApp(config = {}, opts = { openRegister: true }) {
    const store = await setupPosEnv();
    Object.assign(store.config, {
        preparation_printer_ids: [],
        receipt_printer_ids: [],
        ...config,
    });
    await mountPosApp(store);

    if (opts.openRegister) {
        await contains(".screen-login .btn.open-register-btn").click();
        await animationFrame();
    }

    if (config.use_pricelist === false) {
        const order = store.getOrder();
        if (order) {
            order.setPricelist(false);
        }
    }

    return store;
}

export function createCombo(store, config) {
    const {
        name = "Combo",
        items = [],
        basePrice = 10,
        qtyFree = 1,
        qtyMax = 1,
        isUpsell = false,
        sequence = 1,
    } = config;

    const comboItems = items.map((itemConfig) => {
        const comboItem = store.models["product.combo.item"].create({
            combo_id: false,
            product_id: itemConfig.productId || itemConfig.product,
            extra_price: itemConfig.extraPrice || 0,
        });
        return comboItem;
    });

    const combo = store.models["product.combo"].create({
        name,
        combo_item_ids: comboItems,
        base_price: basePrice,
        included_qty: qtyFree,
        qty_max: qtyMax,
        is_upsell: isUpsell,
        sequence,
    });

    comboItems.forEach((item) => {
        item.combo_id = combo;
    });

    return combo;
}

export function createComboTemplate(store, config) {
    const { name = "Combo Template", combos = [], categoryId = 1, price = 50 } = config;

    const createdCombos = combos.map((comboConfig) => {
        if (comboConfig.id && store.models["product.combo"].get(comboConfig.id)) {
            return store.models["product.combo"].get(comboConfig.id);
        }
        return createCombo(store, comboConfig);
    });

    const { template, variant } = createTestProduct(store, {
        name,
        price,
        categoryId,
        type: "combo",
    });
    template.combo_ids = createdCombos;

    return {
        template,
        variant,
        combos: createdCombos,
    };
}

export function createComboItemProduct(store, config) {
    const { name = "Product", price = 10, categoryId = 1 } = config;
    return createTestProduct(store, { name, price, categoryId });
}

export function createComboItemProducts(store, count, config = {}) {
    const products = {};
    const { basePrice = 10, categoryId = 1 } = config;

    for (let i = 1; i <= count; i++) {
        products[i] = createComboItemProduct(store, {
            name: `Product ${i}`,
            price: basePrice + i,
            categoryId,
        });
    }

    return products;
}

export function createAttributeLine(store, attribute, values) {
    return store.models["product.template.attribute.line"].create({
        attribute_id: attribute,
        product_template_value_ids: values,
    });
}

export function createAttribute(store, name, displayType, createVariant = "no_variant") {
    return store.models["product.attribute"].create({
        name,
        display_type: displayType,
        create_variant: createVariant,
        template_value_ids: [],
        attribute_line_ids: [],
    });
}

export function createAttributeValue(store, attribute, name, options = {}) {
    const { id = null, isCustom = false, priceExtra = 0 } = options;
    return store.models["product.template.attribute.value"].create({
        id,
        name,
        attribute_id: attribute,
        is_custom: isCustom,
        price_extra: priceExtra,
        excluded_value_ids: [],
    });
}

export function createTestProduct(store, config = {}) {
    const {
        id = Math.floor(Math.random() * 90000) + 10000,
        name = "Test Product",
        price = 10,
        taxes_id = [],
        categoryId = 1,
        barcode = false,
        default_code = false,
        tracking = "none",
        type = "consu",
        attributes = [],
        uomId = 1,
        image_128 = false,
        pos_optional_product_ids = [],
    } = config;
    const category = store.models["pos.category"].get(categoryId);
    const template = store.models["product.template"].create({
        id,
        name,
        display_name: name,
        available_in_pos: true,
        active: true,
        type,
        uom_id: store.models["uom.uom"].get(uomId) || uomId,
        tracking,
        taxes_id,
        list_price: price,
        pos_categ_ids: category ? [category] : [],
        attribute_line_ids: attributes,
        combo_ids: [],
        product_variant_ids: [],
        pos_sequence: 5,
        sequence: 1,
        image_128,
        pos_optional_product_ids,
    });
    const variant = store.models["product.product"].create({
        id,
        product_tmpl_id: template,
        lst_price: price,
        display_name: name,
        barcode,
        default_code,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: category ? [category.id] : [],
    });
    template.product_variant_ids = [variant];
    return { template, variant };
}

export function createConfigurableChair(store) {
    const color = createAttribute(store, "Color", "color");
    const material = createAttribute(store, "Material", "select");
    const fabric = createAttribute(store, "Fabrics", "radio");
    const options = createAttribute(store, "Options", "multi");

    const blue = createAttributeValue(store, color, "Blue", { id: 9801 });
    const wood = createAttributeValue(store, material, "Wood", { id: 9802 });
    const leather = createAttributeValue(store, fabric, "Leather", { id: 9806 });
    const wool = createAttributeValue(store, fabric, "wool", { id: 9807 });
    const other = createAttributeValue(store, fabric, "Other", { id: 9803, isCustom: true });
    const cushion = createAttributeValue(store, options, "Cushion", { id: 9804 });
    const headrest = createAttributeValue(store, options, "Headrest", { id: 9805 });

    const template = store.models["product.template"].get(5);
    template.update({
        attribute_line_ids: [
            createAttributeLine(store, color, [blue]),
            createAttributeLine(store, material, [wood]),
            createAttributeLine(store, fabric, [leather, wool, other]),
            createAttributeLine(store, options, [cushion, headrest]),
        ],
        name: "Configurable Chair",
        display_name: "Configurable Chair",
    });

    return {
        template,
        values: { blue, wood, leather, wool, other, cushion, headrest },
        payload: {
            attribute_value_ids: [blue.id, wood.id, other.id, cushion.id, headrest.id],
            attribute_custom_values: { [other.id]: "Azerty" },
            price_extra: 0,
            qty: 1,
        },
    };
}

export function createSimpleComboItem(store, id, name) {
    const { variant } = createTestProduct(store, { id, name, price: 10 });
    return store.models["product.combo.item"].create({
        id: id + 100,
        combo_id: false,
        product_id: variant,
        extra_price: 0,
    });
}

export function createComboProductWithAttribute(store, configurableProduct) {
    const { variant: variant2 } = createTestProduct(store, {
        id: 9821,
        name: "Combo Product 2",
        price: 10,
    });
    const { variant: variant6 } = createTestProduct(store, {
        id: 9823,
        name: "Combo Product 6",
        price: 10,
    });

    const combo1 = createCombo(store, {
        name: "Combo 1",
        items: [{ product: variant2 }],
        basePrice: 10,
        qtyFree: 1,
        qtyMax: 1,
        isUpsell: false,
        sequence: 1,
    });

    const combo2 = createCombo(store, {
        name: "Combo 2",
        items: [{ product: configurableProduct.template.product_variant_ids[0] }],
        basePrice: 10,
        qtyFree: 1,
        qtyMax: 2,
        isUpsell: false,
        sequence: 2,
    });

    const combo3 = createCombo(store, {
        name: "Combo 3",
        items: [{ product: variant6 }],
        basePrice: 10,
        qtyFree: 1,
        qtyMax: 1,
        isUpsell: false,
        sequence: 3,
    });

    const { template: comboTemplate } = createTestProduct(store, {
        id: 9865,
        name: "Office Combo Test",
        price: 30,
        type: "combo",
    });
    comboTemplate.combo_ids = [combo1, combo2, combo3];

    return {
        template: comboTemplate,
        items: {
            product2: combo1.combo_item_ids[0],
            configurableChair: combo2.combo_item_ids[0],
            product6: combo3.combo_item_ids[0],
        },
    };
}

export function expectConfiguredChairLine(line) {
    expect(line.getFullProductName()).toBe(
        "Configurable Chair (Blue, Wood, Fabrics: Other: Azerty, Cushion, Headrest)"
    );
    expect(line.selectedAttributes[line.attribute_value_ids[0].attribute_id.id].selected.name).toBe(
        "Blue"
    );
    expect(line.custom_attribute_value_ids[0].custom_product_template_attribute_value_id.name).toBe(
        "Other"
    );
    expect(line.custom_attribute_value_ids[0].custom_value).toBe("Azerty");
}

export function createComboSetup(store, config) {
    const { id: baseId, name, combos: comboDefs, price = 50, categoryId = 1 } = config;

    const products = [];
    const comboItems = [];
    const combos = [];
    let productIdCounter = baseId + 300;

    for (const comboDef of comboDefs) {
        const comboItemDefs = comboDef.items.map((itemDef) => {
            const { template, variant } = createTestProduct(store, {
                id: productIdCounter++,
                name: itemDef.name,
                price: itemDef.price || 10,
                categoryId,
            });
            products.push({ template, variant });
            return { product: variant, extraPrice: itemDef.extraPrice || 0 };
        });

        const combo = createCombo(store, {
            name: comboDef.name,
            items: comboItemDefs,
            basePrice: comboDef.basePrice || 10,
            qtyFree: comboDef.qtyFree ?? 1,
            qtyMax: comboDef.qtyMax ?? 1,
            isUpsell: comboDef.isUpsell || false,
            sequence: comboDef.sequence || combos.length + 1,
        });

        combo.combo_item_ids.forEach((ci) => {
            comboItems.push(ci);
            const matchingProduct = products.find((p) => p.variant.id === ci.product_id.id);
            if (matchingProduct) {
                matchingProduct.comboItem = ci;
            }
        });
        combos.push(combo);
    }

    const { template: comboTemplate, variant: comboVariant } = createTestProduct(store, {
        id: baseId,
        name,
        price,
        categoryId,
        type: "combo",
    });
    comboTemplate.combo_ids = combos;

    return { template: comboTemplate, variant: comboVariant, combos, products, comboItems };
}

export function createPosTestTax(store, config = {}) {
    const {
        id,
        name = "Tax",
        amount = 10,
        priceInclude = false,
        includeBaseAmount = false,
        fiscalPositionIds = [],
        originalTaxIds = [],
    } = config;
    const opts = {
        name,
        amount,
        price_include: priceInclude,
        price_include_override: priceInclude ? "tax_included" : "tax_excluded",
        include_base_amount: includeBaseAmount,
        is_base_affected: true,
        has_negative_factor: false,
        amount_type: "percent",
        type_tax_use: "sale",
        company_id: 250,
        sequence: 1,
        tax_group_id: 1,
        fiscal_position_ids: fiscalPositionIds,
        original_tax_ids: originalTaxIds,
    };
    if (id !== undefined) {
        opts.id = id;
    }
    return store.models["account.tax"].create(opts);
}

export function createFiscalPosition(store, config = {}) {
    const { id, name = "Fiscal Position", taxMap = {} } = config;
    const opts = {
        name,
        display_name: name,
        tax_map: taxMap,
    };
    if (id !== undefined) {
        opts.id = id;
    }
    return store.models["account.fiscal.position"].create(opts);
}

export function enableCashRounding(store, method = "UP", onlyCash = true) {
    const rounding = store.models["account.cash.rounding"].create({
        name: `Rounding ${method.toLowerCase()}`,
        rounding: 0.05,
        rounding_method: method,
    });
    store.config.rounding_method = rounding;
    store.config.cash_rounding = true;
    store.config.only_round_cash_method = onlyCash;
    return rounding;
}
