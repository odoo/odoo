import { MockServer } from "@web/../tests/web_test_helpers";

export const addProductLineToOrder = async (
    store,
    order,
    { templateId = 60, productId = 60, qty = 1, price_unit = 10, ...extraFields } = {}
) => {
    const template = store.models["product.template"].get(templateId);
    const product = store.models["product.product"].get(productId);

    const lineData = {
        product_tmpl_id: template,
        product_id: product,
        qty,
        price_unit,
        ...extraFields,
    };

    const line = await store.addLineToOrder(lineData, order, {}, false);

    return line;
};

export const deactivateAllProgramsExcept = (store, keepIds) => {
    const to_delete = store.models["loyalty.program"]
        .getAllIds()
        .filter((id) => !keepIds.includes(id));
    store.models["loyalty.program"].deleteMany(store.models["loyalty.program"].readMany(to_delete));
};

export function clearLoyaltyData() {
    for (const modelName of ["loyalty.card", "loyalty.reward", "loyalty.rule", "loyalty.program"]) {
        const ids = MockServer.env[modelName].search([]);
        if (ids.length) {
            MockServer.env[modelName].unlink(ids);
        }
    }
}

export function createPartner(values = {}) {
    return MockServer.env["res.partner"].create({
        name: "Test Partner",
        ...values,
    });
}

export function createPosProduct({ name = "Test Product", list_price = 0, ...values } = {}) {
    const posCategIds = values.pos_categ_ids ?? [1];
    const templateId = MockServer.env["product.template"].create({
        name,
        display_name: name,
        list_price,
        standard_price: 0,
        categ_id: false,
        barcode: false,
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
        pos_categ_ids: posCategIds,
        taxes_id: [],
        attribute_line_ids: [],
        active: true,
        image_128: false,
        public_description: false,
        pos_optional_product_ids: [],
        sequence: 1,
        product_tag_ids: [],
        ...values,
    });
    const productId = MockServer.env["product.product"].create({
        product_tmpl_id: templateId,
        lst_price: list_price,
        standard_price: 0,
        display_name: name,
        product_tag_ids: [],
        barcode: false,
        pos_categ_ids: posCategIds,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        ...values,
    });
    MockServer.env["product.template"].write([templateId], {
        product_variant_ids: [productId],
    });

    return { templateId, productId };
}

export function createLoyaltyCard(values = {}) {
    return MockServer.env["loyalty.card"].create({
        code: false,
        points: 0,
        partner_id: false,
        program_id: false,
        expiration_date: false,
        ...values,
    });
}

export function createLoyaltyProgram({
    programValues = {},
    ruleValues = [{}],
    rewardValues = [{}],
} = {}) {
    const programType = programValues.program_type || "promotion";
    const trigger = programValues.trigger || "auto";
    const programId = MockServer.env["loyalty.program"].create({
        name: "Test Loyalty Program",
        currency_id: 1,
        trigger,
        applies_on: programType === "loyalty" ? "both" : "current",
        program_type: programType,
        is_nominative: programType === "loyalty",
        portal_visible: false,
        pricelist_ids: [],
        trigger_product_ids: [],
        is_payment_program: false,
        ...programValues,
    });

    const ruleIds = ruleValues.map((ruleValue) => {
        const productIds = ruleValue.product_ids || [];
        return MockServer.env["loyalty.rule"].create({
            program_id: programId,
            any_product: !productIds.length,
            product_ids: productIds,
            valid_product_ids: ruleValue.valid_product_ids || productIds,
            product_category_id: false,
            product_tag_id: false,
            reward_point_mode: "order",
            reward_point_amount: 1,
            reward_point_split: false,
            minimum_qty: 0,
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: trigger === "with_code" ? "with_code" : "auto",
            code: false,
            promo_barcode: false,
            ...ruleValue,
        });
    });

    const rewardIds = rewardValues.map((rewardValue) => {
        const rewardProductIds =
            rewardValue.reward_product_ids ||
            (rewardValue.reward_product_id ? [rewardValue.reward_product_id] : []);
        const discountProductIds = rewardValue.discount_product_ids || [];
        const discountLineProductId =
            rewardValue.discount_line_product_id ||
            createPosProduct({
                name: rewardValue.description || "Discount Line Product",
                list_price: 0,
                available_in_pos: false,
                pos_categ_ids: [],
                taxes_id: [],
                type: "service",
            }).productId;
        return MockServer.env["loyalty.reward"].create({
            program_id: programId,
            description: "10 on your order",
            reward_type: "discount",
            required_points: 1,
            clear_wallet: false,
            discount: 10,
            discount_mode: "per_order",
            discount_applicability: "order",
            discount_max_amount: 0,
            discount_line_product_id: discountLineProductId,
            discount_product_ids: discountProductIds,
            is_global_discount: true,
            reward_product_id: rewardValue.reward_product_id || false,
            reward_product_ids: rewardProductIds,
            reward_product_qty: 1,
            reward_product_tag_id: false,
            reward_product_domain: "null",
            multi_product: false,
            all_discount_product_ids: rewardValue.all_discount_product_ids || discountProductIds,
            ...rewardValue,
        });
    });

    MockServer.env["loyalty.program"].write([programId], {
        rule_ids: ruleIds,
        reward_ids: rewardIds,
    });

    return { programId, ruleIds, rewardIds };
}
