import { uuidv4 } from "@point_of_sale/utils";
import {
    getService,
    makeDialogMockEnv,
    mountWithCleanup,
    patchWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { animationFrame, tick, waitFor, waitUntil } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import { expect } from "@odoo/hoot";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display";

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

    await makeDialogMockEnv();
    onRpc("/css", () => "");
    const store = getService("pos");
    store.setCashier(store.user);
    patchWithCleanup(user, {
        // Needed for the allowProductCreation method
        // and for product reorder in the frontend
        checkAccessRight: (model, operation) =>
            (operation === "create" && model === "product.product") ||
            (operation === "write" && model === "product.template"),
    });
    patchWithCleanup(store.router, {
        navigate(routeName, routeParams = {}) {
            this.state.current = routeName;
            this.state.params = routeParams;
        },
    });
    return store;
};

export async function scanBarcode(store, barcode) {
    store.env.services.barcode.bus.trigger("barcode_scanned", { barcode });
    await new Promise((resolve) => requestAnimationFrame(resolve));
}

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

export async function waitUntilOrdersSynced(store, options) {
    await waitUntil(() => !store.syncingOrders.size, options);
    await tick();
}

export const mountPosDialog = async (component, props) => {
    patchDialogComponent(component);
    const dialog = getService("dialog");
    const root = await mountWithCleanup(MainComponentsContainer);
    const deferred = new Deferred();

    const getComponentInstance = (root) => {
        const flattenedChildren = (comp, acc = {}) => {
            const array = Object.values(comp.children);
            for (const child of array) {
                acc[child.componentName] = child;
                flattenedChildren(child, acc);
            }
            return acc;
        };
        const components = flattenedChildren(root);
        return components[component.name];
    };

    dialog.add(component, {
        ...props,
        onMounted() {
            const dialogComponent = getComponentInstance(root.__owl__);
            deferred.resolve(dialogComponent.component);
        },
    });
    return await deferred;
};

export const patchDialogComponent = (component) => {
    if (Array.isArray(component.props)) {
        component.props = [...component.props, "onMounted?"];
    } else {
        component.props = {
            ...component.props,
            onMounted: { optional: true },
        };
    }
    patch(component.prototype, {
        setup() {
            super.setup();

            onMounted(() => {
                this.props.onMounted && this.props.onMounted();
            });
        },
    });
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

export const mountCustomerDisplayWithOrder = async (orderData = {}) => {
    patchWithCleanup(session, {
        company_id: 1,
        config_id: 1,
        has_bg_img: false,
        customer_display_bg_img: false,
    });

    const customerDisplayData = getService("customer_display_data");
    for (const key of Object.keys(customerDisplayData)) {
        delete customerDisplayData[key];
    }
    Object.assign(customerDisplayData, {
        finalized: false,
        lines: [],
        paymentLines: [],
        qrPaymentData: null,
        onlinePaymentData: null,
        displayScreenSaver: false,
        ...orderData,
    });

    return mountWithCleanup(CustomerDisplay);
};

/**
 * Utility functions for creating combo products and items in Hoot tests
 */

/**
 * Create a combo product with items
 * @param {Object} store - POS store instance
 * @param {Object} config - Configuration object
 * @param {string} config.name - Combo name
 * @param {Array<Object>} config.items - Array of combo items config
 * @param {number} config.basePrice - Base price of combo
 * @param {number} config.qtyFree - Quantity included for free
 * @param {number} config.qtyMax - Maximum quantity
 * @param {boolean} config.isUpsell - Is this an upsell combo
 * @param {number} config.sequence - Combo sequence
 * @param {number} config.categoryId - POS category ID
 * @returns {Object} Created combo object
 */
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

    // Create combo items
    const comboItems = items.map((itemConfig) => {
        const comboItem = store.models["product.combo.item"].create({
            combo_id: false,
            product_id: itemConfig.productId || itemConfig.product,
            extra_price: itemConfig.extraPrice || 0,
        });
        return comboItem;
    });

    // Create combo
    const combo = store.models["product.combo"].create({
        name,
        combo_item_ids: comboItems,
        base_price: basePrice,
        qty_free: qtyFree,
        qty_max: qtyMax,
        is_upsell: isUpsell,
        sequence,
    });

    // Link items back to combo
    comboItems.forEach((item) => {
        item.combo_id = combo;
    });

    return combo;
}

/**
 * Create a combo product template with multiple combos
 * @param {Object} store - POS store instance
 * @param {Object} config - Configuration object
 * @param {string} config.name - Template name
 * @param {Array<Object>} config.combos - Array of combo configurations
 * @param {number} config.categoryId - POS category ID
 * @returns {Object} Created combo template with product variant
 */
export function createComboTemplate(store, config) {
    const { name = "Combo Template", combos = [], categoryId = 1 } = config;

    // Create combos if not already created
    const createdCombos = combos.map((comboConfig) => {
        if (comboConfig.id && store.models["product.combo"].get(comboConfig.id)) {
            return store.models["product.combo"].get(comboConfig.id);
        }
        return createCombo(store, comboConfig);
    });

    // Create combo template
    const template = store.models["product.template"].create({
        name,
        display_name: name,
        available_in_pos: true,
        active: true,
        type: "combo",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [],
        attribute_line_ids: [],
        combo_ids: createdCombos,
        pos_categ_ids: [store.models["pos.category"].get(categoryId)],
    });

    // Create variant
    const variant = store.models["product.product"].create({
        name,
        product_tmpl_id: template,
        display_name: name,
        lst_price: 50,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(categoryId)],
    });

    template.product_variant_ids = [variant];

    return {
        template,
        variant,
        combos: createdCombos,
    };
}

/**
 * Create a simple product for combo items
 * @param {Object} store - POS store instance
 * @param {Object} config - Configuration object
 * @returns {Object} Created product template and variant
 */
export function createComboItemProduct(store, config) {
    const { name = "Product", price = 10, categoryId = 1 } = config;

    const template = store.models["product.template"].create({
        name,
        display_name: name,
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [],
        attribute_line_ids: [],
        combo_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(categoryId)],
    });

    const variant = store.models["product.product"].create({
        name,
        product_tmpl_id: template,
        display_name: name,
        lst_price: price,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(categoryId)],
    });

    template.product_variant_ids = [variant];

    return { template, variant };
}

/**
 * Helper to create multiple products for use in combos
 * @param {Object} store - POS store instance
 * @param {number} count - Number of products to create
 * @param {Object} config - Base configuration
 * @returns {Array<Object>} Array of created products
 */
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

/**
 * Create a complete combo setup with products, combos, and template
 * @param {Object} store - POS store instance
 * @param {Object} config - Configuration object
 * @returns {Object} Complete combo setup
 */
export function createCompleteComboSetup(store, config = {}) {
    const {
        templateName = "Complete Combo",
        numProducts = 9,
        categoryId = 1,
        combos = [
            {
                name: "First Combo",
                itemIndices: [1, 2, 3],
                basePrice: 25,
                qtyFree: 1,
                qtyMax: 1,
                isUpsell: false,
            },
            {
                name: "Second Combo",
                itemIndices: [4, 5],
                basePrice: 30,
                qtyFree: 1,
                qtyMax: 1,
                isUpsell: false,
            },
            {
                name: "Third Combo",
                itemIndices: [6, 7, 8, 9],
                basePrice: 50,
                qtyFree: 1,
                qtyMax: 1,
                isUpsell: false,
            },
        ],
    } = config;

    // Create products
    const products = createComboItemProducts(store, numProducts, {
        basePrice: 10,
        categoryId,
    });

    // Create combos
    const createdCombos = combos.map((comboConfig, idx) => {
        const itemsConfig = comboConfig.itemIndices.map((itemIdx, itemPos) => ({
            productId: products[itemIdx].variant,
            extraPrice: itemPos === comboConfig.itemIndices.length - 1 ? 2 : 0,
        }));

        return createCombo(store, {
            name: comboConfig.name,
            items: itemsConfig,
            basePrice: comboConfig.basePrice,
            qtyFree: comboConfig.qtyFree,
            qtyMax: comboConfig.qtyMax,
            isUpsell: comboConfig.isUpsell,
            sequence: idx + 1,
        });
    });

    // Create template
    const templateData = createComboTemplate(store, {
        name: templateName,
        combos: createdCombos,
        categoryId,
    });

    return {
        products,
        combos: createdCombos,
        template: templateData.template,
        variant: templateData.variant,
    };
}

/**
 * Create an attribute line for a product template
 * @param {Object} store - POS store instance
 * @param {Object} attribute - Product attribute
 * @param {Array} values - Attribute values
 * @returns {Object} Created attribute line
 */
export function createAttributeLine(store, attribute, values) {
    return store.models["product.template.attribute.line"].create({
        attribute_id: attribute,
        product_template_value_ids: values,
    });
}

/**
 * Create an attribute for products
 * @param {Object} store - POS store instance
 * @param {string} name - Attribute name
 * @param {string} displayType - Display type (radio, select, color, etc.)
 * @param {string} createVariant - Variant creation mode (no_variant, always, etc.)
 * @returns {Object} Created attribute
 */
export function createAttribute(store, name, displayType, createVariant = "no_variant") {
    return store.models["product.attribute"].create({
        name,
        display_type: displayType,
        create_variant: createVariant,
        template_value_ids: [],
        attribute_line_ids: [],
    });
}

/**
 * Create an attribute value
 * @param {Object} store - POS store instance
 * @param {Object} attribute - Product attribute
 * @param {string} name - Value name
 * @param {Object} options - Additional options (id, isCustom, priceExtra)
 * @returns {Object} Created attribute value
 */
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
