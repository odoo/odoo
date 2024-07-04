import { negate } from "@point_of_sale/../tests/tours/utils/common";

const productTrigger = (productName) =>
    `label.combo-line:has(article.product .product-name:contains("${productName}"))`;
const isComboSelectedTrigger = (productName) => `input:checked ~ ${productTrigger(productName)}`;
const confirmationButtonTrigger = `footer button.confirm`;

export function select(productName) {
    return {
        content: `Select combo item ${productName}`,
        trigger: `.modal ${productTrigger(productName)}`,
        in_modal: false,
        run: "click",
    };
}
export function isSelected(productName) {
    return {
        content: `Check that ${productName} is selected`,
        trigger: `.modal ${isComboSelectedTrigger(productName)}`,
        in_modal: false,
        run: "click",
    };
}
export function isNotSelected(productName) {
    return {
        content: `Check that ${productName} is not selected`,
        trigger: `.modal ${negate(isComboSelectedTrigger(productName), ".modal-body")}`,
        in_modal: false,
        run: "click",
    };
}
export function isConfirmationButtonDisabled() {
    return {
        content: "try to click `confirm` without having made all the selections",
        trigger: `.modal ${confirmationButtonTrigger}[disabled]`,
        in_modal: false,
        allowDisabled: true,
    };
}
