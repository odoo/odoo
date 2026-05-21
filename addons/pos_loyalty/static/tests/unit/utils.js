import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains, getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

const { DateTime } = luxon;

function toIds(records = []) {
    return records.map((record) => record?.id ?? record);
}

/**
 * Utility to create a new order with loyalty flow.
 *
 * @param {Object} store
 * @param {Array} products
 * @param {Array} rewardLines
 * @param {Object|null} partner
 * @returns {Object} order
 */
export async function createOrderWithLoyalty(
    store,
    products = [],
    partner = null,
    rewardLines = []
) {
    store.addNewOrder();
    const order = store.getOrder();

    if (partner) {
        order.setPartner(partner);
    }

    const date = DateTime.now();
    order.write_date = date;
    order.create_date = date;

    // Add normal products through store flow
    for (const p of products) {
        const product = p.product;

        await store.addLineToCurrentOrder(
            {
                product_id: product,
                product_tmpl_id: product.product_tmpl_id,
                qty: p.qty || 1,
            },
            {
                price_unit: p.price,
            }
        );
    }

    // Add reward lines manually
    for (const line of rewardLines) {
        order.addOrderline(
            await store.models["pos.order.line"].create({
                product_id: line.product_id,
                qty: line.qty || 1,
                price_unit: line.price_unit || 0,
                is_reward_line: line.is_reward_line || false,
                reward_id: line.reward_id || null,
                price_type: line.price_type || "automatic",
                order_id: order,
            })
        );
    }

    return order;
}

export async function getFilledOrderLoyalty(store) {
    return await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 3, price: 100 },
        { product: store.models["product.product"].get(6), qty: 2, price: 100 },
    ]);
}

export function createPartner(store, values = {}) {
    return store.models["res.partner"].create({
        name: "Test Partner",
        ...values,
    });
}

export function clearLoyaltyData(store) {
    for (const modelName of ["loyalty.card", "loyalty.reward", "loyalty.rule", "loyalty.program"]) {
        for (const record of [...store.models[modelName].getAll()]) {
            record.delete();
        }
    }
    store.partnerId2CouponIds = {};
}

export function createPosProduct(store, values = {}) {
    const posCategory = values.posCategory || store.models["pos.category"].get(1);
    const posCategoryId = posCategory?.id || posCategory;
    const listPrice = values.list_price ?? 0;
    const name = values.name || "Test Product";
    const productTemplate = store.models["product.template"].create({
        standard_price: 0,
        categ_id: false,
        barcode: false,
        name,
        display_name: name,
        list_price: listPrice,
        is_favorite: false,
        default_code: false,
        to_weight: false,
        uom_id: 1,
        description_sale: false,
        description: false,
        type: "consu",
        service_tracking: "no",
        is_storable: false,
        color: 0,
        pos_sequence: 1,
        available_in_pos: true,
        pos_categ_ids: [posCategoryId],
        taxes_id: [],
        attribute_line_ids: [],
        active: true,
        image_128: false,
        public_description: false,
        pos_optional_product_ids: [],
        sequence: 1,
        product_tag_ids: [],
        ...values.productValues,
    });
    const product = store.models["product.product"].create({
        product_tmpl_id: productTemplate,
        lst_price: listPrice,
        standard_price: 0,
        display_name: name,
        product_tag_ids: [],
        barcode: false,
        pos_categ_ids: [posCategoryId],
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        ...values.productValues,
    });
    productTemplate.update({
        product_variant_ids: [product],
    });

    return { productTemplate, product };
}

export function createLoyaltyCard(store, values = {}) {
    return store.models["loyalty.card"].create({
        code: null,
        points: 0,
        partner_id: null,
        program_id: null,
        expiration_date: null,
        ...values,
    });
}

export function createLoyaltyProgram(
    store,
    { programValues = {}, ruleValues = [{}], rewardValues = [{}] } = {}
) {
    const normalizedProgramValues = {
        ...programValues,
        pricelist_ids: toIds(programValues.pricelist_ids || []),
        trigger_product_ids: toIds(programValues.trigger_product_ids || []),
    };
    const programType = normalizedProgramValues.program_type || "promotion";
    const program = store.models["loyalty.program"].create({
        name: "Test Loyalty Program",
        trigger: "auto",
        applies_on: programType === "loyalty" ? "both" : "current",
        program_type: programType,
        is_nominative: programType === "loyalty",
        portal_visible: false,
        pricelist_ids: [],
        trigger_product_ids: [],
        is_payment_program: false,
        total_order_count: 0,
        ...normalizedProgramValues,
    });

    const rules = ruleValues.map((ruleValue) => {
        const productIds = toIds(ruleValue.product_ids || []);
        const validProductIds = toIds(ruleValue.valid_product_ids || productIds);
        const rule = store.models["loyalty.rule"].create({
            program_id: program,
            any_product: !productIds.length,
            product_ids: productIds,
            valid_product_ids: validProductIds,
            product_category_id: false,
            product_tag_id: false,
            reward_point_mode: "order",
            reward_point_amount: 1,
            reward_point_split: false,
            minimum_qty: 0,
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: program.trigger === "with_code" ? "with_code" : "auto",
            code: false,
            promo_barcode: false,
            ...ruleValue,
        });
        rule.validProductIds = new Set(validProductIds);
        return rule;
    });

    const rewards = rewardValues.map((rewardValue) => {
        const rewardProductId = rewardValue.reward_product_id?.id ?? rewardValue.reward_product_id;
        const rewardProductIds = toIds(
            rewardValue.reward_product_ids || (rewardProductId ? [rewardProductId] : [])
        );
        const discountProductIds = toIds(rewardValue.discount_product_ids || []);
        const allDiscountProductIds = toIds(
            rewardValue.all_discount_product_ids || discountProductIds
        );
        const discountLineProduct =
            rewardValue.discount_line_product_id ||
            createPosProduct(store, {
                name: rewardValue.description || "Discount Line Product",
                list_price: 0,
                productValues: {
                    available_in_pos: false,
                    pos_categ_ids: [],
                    taxes_id: [],
                    type: "service",
                },
            }).product;
        return store.models["loyalty.reward"].create({
            program_id: program,
            description: "10 on your order",
            reward_type: "discount",
            required_points: 1,
            clear_wallet: false,
            discount: 10,
            discount_mode: "per_order",
            discount_applicability: "order",
            discount_max_amount: 0,
            discount_line_product_id: discountLineProduct,
            discount_product_ids: discountProductIds,
            is_global_discount: true,
            reward_product_id: rewardProductId || false,
            reward_product_ids: rewardProductIds,
            reward_product_qty: 1,
            reward_product_tag_id: false,
            reward_product_domain: "null",
            multi_product: false,
            all_discount_product_ids: allDiscountProductIds,
            ...rewardValue,
        });
    });

    program.update({
        rule_ids: rules.map((rule) => rule.id),
        reward_ids: rewards.map((reward) => reward.id),
    });

    return { program, rules, rewards };
}

export function createLoyaltyProgramWithRuleAndReward(
    store,
    { programValues = {}, ruleValues = {}, rewardValues = {} } = {}
) {
    const { program, rules, rewards } = createLoyaltyProgram(store, {
        programValues,
        ruleValues: [ruleValues],
        rewardValues: [rewardValues],
    });

    return { program, rule: rules[0], reward: rewards[0] };
}

export async function refreshLoyaltyState(store) {
    for (const rule of store.models["loyalty.rule"].getAll()) {
        rule.validProductIds = new Set(toIds(rule.valid_product_ids || []));
    }

    store.partnerId2CouponIds = {};
    store.computePartnerCouponIds();

    for (const reward of store.models["loyalty.reward"].getAll()) {
        reward.all_discount_product_ids = reward.discount_product_ids;
    }
    store.computeDiscountProductIdsForAllRewards();

    if (store.getOrder()) {
        await store.updatePrograms();
        await store.updateRewards();
    }
}

export async function mountProductScreen(store) {
    return mountWithCleanup(ProductScreen, {
        props: { orderUuid: store.getOrder().uuid },
    });
}

function isMobileProductScreen() {
    return getService("ui").isSmall;
}

async function ensureProductScreenPane(targetPane) {
    if (!isMobileProductScreen()) {
        return;
    }
    const pos = getService("pos");
    if (pos.mobile_pane !== targetPane) {
        pos.switchPane();
        await animationFrame();
    }
}

export async function clickProductScreenPartnerButton() {
    await ensureProductScreenPane("left");
    await contains(".product-screen .set-partner").click();
    await animationFrame();
    await waitFor(".partner-list");
}

export async function selectProductScreenCustomer(name) {
    if (!document.querySelector(".partner-list")) {
        await clickProductScreenPartnerButton();
    }
    await contains(`.partner-info:contains("${name}")`).click();
    await animationFrame();
}

export async function clickDisplayedProduct(name) {
    await ensureProductScreenPane("right");
    await contains(`article.product .product-name:contains("${name}")`).click();
    await animationFrame();
}

export async function selectOrderline(name, { reward = false } = {}) {
    await ensureProductScreenPane("left");
    const selector = reward
        ? `.orderline.fst-italic .product-name:contains("${name}")`
        : `.orderline:not(.fst-italic) .product-name:contains("${name}")`;

    await contains(selector).click();
    await animationFrame();
}

export async function clickNumpad(...keys) {
    await ensureProductScreenPane("left");
    const normalizedKeys = keys
        .flatMap((key) => {
            const value = key.toString();
            return /^-?\d*\.?\d+$/.test(value) ? value.split("") : [value];
        })
        .map((key) => (key === "-" ? "+/-" : key));

    for (const key of normalizedKeys) {
        await contains(`.numpad button:contains("${key}")`).click();
        await animationFrame();
    }
}

export async function addOrderlineFromProductScreen(productName, { quantity = 1, unitPrice } = {}) {
    await clickDisplayedProduct(productName);

    if (unitPrice !== undefined) {
        await clickNumpad("Price", unitPrice, "Qty");
    }
    if (quantity.toString() !== "1") {
        await clickNumpad(quantity);
    }
}

export async function openProductScreenActions() {
    if (!document.querySelector(".control-buttons-modal")) {
        await ensureProductScreenPane("left");
        await contains(
            isMobileProductScreen()
                ? ".product-screen .mobile-more-button"
                : ".product-screen .more-btn"
        ).click();
        await animationFrame();
        await waitFor(".control-buttons-modal");
    }
}

export async function clickProductScreenAction(label) {
    await openProductScreenActions();
    await contains(`.control-buttons-modal .control-button:contains("${label}")`).click();
    await animationFrame();
}

export async function clickSelectionPopupItem(label) {
    await waitFor(".selection-item");
    await contains(`.selection-item:contains("${label}")`).click();
    await animationFrame();
}

export async function confirmDialog(buttonText = "Ok") {
    await waitFor(".modal");
    await contains(`.modal .btn:contains("${buttonText}")`).click();
    await animationFrame();
}

export async function enterCodeFromProductScreen(code) {
    await clickProductScreenAction("Enter Code");
    await waitFor(".modal textarea");
    await contains(".modal textarea").edit(code);
    await contains('.modal .btn-primary:contains("Apply")').click();
    await animationFrame();
}

export async function claimRewardFromProductScreen(label) {
    await clickProductScreenAction("Reward");
    await clickSelectionPopupItem(label);
}

export async function scanBarcode(store, barcode) {
    store.env.services.barcode.bus.trigger("barcode_scanned", { barcode });
    await new Promise((resolve) => requestAnimationFrame(resolve));
}
