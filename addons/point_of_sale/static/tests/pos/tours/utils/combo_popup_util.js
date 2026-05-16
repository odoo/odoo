import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

const productTrigger = (productName) =>
    `article.product:has(.product-name:contains("${productName}"))`;
const isComboSelectedTrigger = (productName) =>
    `label.combo-item.selected ${productTrigger(productName)}`;
const confirmationButtonTrigger = `footer button.confirm`;

export function select(productName) {
    return {
        content: `Select combo item ${productName}`,
        trigger: `.modal label.combo-item ${productTrigger(productName)}`,
        run: "click",
    };
}
export function isSelected(productName) {
    return {
        content: `Check that ${productName} is selected`,
        trigger: `.modal ${isComboSelectedTrigger(productName)}`,
    };
}
export function isNotSelected(productName) {
    return {
        content: `Check that ${productName} is not selected`,
        trigger: `.modal ${negate(isComboSelectedTrigger(productName), ".modal-body")}`,
    };
}
export function isConfirmationButtonDisabled() {
    return {
        content: "try to click `confirm` without having made all the selections",
        trigger: `.modal ${confirmationButtonTrigger}[disabled]`,
    };
}
export function checkTotal(expectedAmount) {
    return {
        content: `Check that combo total amount is $${expectedAmount}`,
        trigger: `.modal div.h3:contains("Total: $ ${expectedAmount}")`,
    };
}
export function clickQtyBtnAdd(productName) {
    return {
        content: `Click the add quantity button for ${productName}`,
        trigger: `.modal article:has(.product-name:contains("${productName}")) button[name="pos_quantity_button_plus"]`,
        run: "click",
    };
}
export function clickQtyBtnMinus(productName) {
    return {
        content: `Click the minus quantity button for ${productName}`,
        trigger: `.modal article:has(.product-name:contains("${productName}")) button[name="pos_quantity_button_minus"]`,
        run: "click",
    };
}
export function checkProductQty(productName, expectedQty) {
    return {
        content: `Check that product ${productName} has quantity ${expectedQty}`,
        trigger: `.modal article:has(.product-name:contains("${productName}")):has(input[name="pos_quantity"])`,
        run: () => {
            const article = [...document.querySelectorAll(".modal article")].find((el) =>
                el.textContent.includes(productName)
            );
            const input = article.querySelector('input[name="pos_quantity"]');
            if (input.value != expectedQty) {
                throw new Error(
                    `Expected ${expectedQty}, but got ${input.value} for "${productName}".`
                );
            }
        },
    };
}
export function checkImgAndSelect(productName, checkImg = false) {
    const productArticleSelector = productTrigger(productName);
    const withImg = `${productArticleSelector}:has(.product-img)`;
    const withoutImg = `${productArticleSelector}:not(:has(.product-img))`;
    const trigger = `.modal ${checkImg ? withImg : withoutImg}`;
    return {
        content: `Check image & select combo item ${productName}`,
        trigger: trigger,
        run: "click",
    };
}
