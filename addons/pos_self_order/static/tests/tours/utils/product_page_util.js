import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

export function clickProduct(productName) {
    return {
        content: `Click on product '${productName}'`,
        trigger: `.product_list .o_self_product_box span:contains('${productName}')`,
        run: "click",
    };
}
export function clickCategory(categoryName) {
    return {
        content: `Click on category '${categoryName}'`,
        trigger: `.category_btn:contains('${categoryName}')`,
        run: "click",
    };
}

export function clickChildCategory(childCategoryName) {
    return {
        content: `Click on child category '${childCategoryName}'`,
        trigger: `.child_category_btn:contains('${childCategoryName}')`,
        run: "click",
    };
}

export function waitProduct(productName) {
    return {
        content: `Wait for product '${productName}'`,
        trigger: `.o_self_product_box span:contains('${productName}')`,
    };
}

export function checkReferenceNotInProductName(productName, reference) {
    return {
        content: `Check product label has '${productName}' and not ${reference}`,
        trigger: `.o_self_product_box span:contains('${productName}'):not(:contains("${reference}"))`,
    };
}

export function clickBack() {
    return {
        content: `Click on back button`,
        trigger: `.btn.btn-back`,
        run: "click",
    };
}

export function clickCancel() {
    return [
        {
            content: `Click on Cancel button`,
            trigger: `.btn.btn-cancel`,
            run: "click",
        },
        {
            content: `Click on button Cancel Order`,
            trigger: `.btn.btn-primary:contains('Cancel Order')`,
            run: "click",
        },
    ];
}

export function checkOrderTotal(amount) {
    return {
        content: `Confirm '${amount}' is displayed correctly`,
        trigger: `.o_self_product_list_page .o_self_shadow_bottom .o-so-tabular-nums:contains('${amount}')`,
    };
}

export function checkProductQty(productName, qty) {
    return {
        content: `Confirm product '${qty}' is displayed correctly`,
        trigger: `.o_self_product_list_page .o_self_product_box:has(.self_order_product_name:contains('${productName}')) .badge:contains('${qty}')`,
    };
}

export function clickDiscard() {
    return {
        content: "Click on Discard button",
        trigger: ".btn.btn-link .oi-close",
        run: "click",
    };
}

export function setupAttribute(attributes) {
    return attributes.map((attr) => ({
        content: `Select value ${attr.value} for attribute ${attr.name}`,
        trigger: `h2:contains("${attr.name}") + div.row button:contains("${attr.value}")`,
        run: "click",
    }));
}

export function attributeHasColorDot(attribute) {
    return {
        content: `The ${attribute} has a color dot`,
        trigger: `div:has(span:contains("${attribute}")) ~ div.rounded-5`,
    };
}

export function attributeHasImage(attribute) {
    return {
        content: `The ${attribute} has an image`,
        trigger: `div:has(span:contains("${attribute}")) ~ img.rounded-4`,
    };
}

export function clickComboProduct(productName) {
    return {
        content: `Click on combo product '${productName}'`,
        trigger: `.combo_product_box span:contains('${productName}')`,
        run: "click",
    };
}

export function setupCombo(products) {
    const steps = [];

    for (const product of products) {
        steps.push(clickComboProduct(product.product));

        if (product.attributes.length > 0) {
            Utils.checkMissingRequiredsExists();
            steps.push(...setupAttribute(product.attributes));
            negateStep(Utils.checkMissingRequiredsExists());
        }
    }

    return steps;
}

export function isProductDisplayed(productName) {
    return {
        content: `Check if product '${productName}' is displayed`,
        trigger: `.o_self_product_box span:contains("${productName}")`,
    };
}

export function checkNthProduct(n, name) {
    return {
        content: `Product ${n} should be ${name}`,
        trigger: `.product_list .o_self_product_box:nth-child(${n}) span:contains('${name}')`,
    };
}

export function isShown() {
    return {
        content: "Check whether the Product List page is displayed",
        trigger: ".o_self_product_list_page",
    };
}
