import { negate } from "@point_of_sale/../tests/tours/utils/common";

const productTrigger = (productName) =>
    `label.combo-line:has(article.product .product-name:contains("${productName}"))`;
const isComboSelectedTrigger = (productName) => `input:checked ~ ${productTrigger(productName)}`;
const confirmationButtonTrigger = `footer button.confirm`;

export function select(productName) {
    return {
        content: `Select combo item ${productName}`,
        trigger: productTrigger(productName),
        in_modal: true,
    };
}
export function isSelected(productName) {
    return {
        content: `Check that ${productName} is selected`,
        trigger: isComboSelectedTrigger(productName),
        isCheck: true,
        in_modal: true,
    };
}
export function isNotSelected(productName) {
    return {
        content: `Check that ${productName} is not selected`,
        trigger: negate(isComboSelectedTrigger(productName), ".modal-body"),
        isCheck: true,
        in_modal: true,
    };
}
export function isConfirmationButtonDisabled() {
    return {
        content: "try to click `confirm` without having made all the selections",
        trigger: `${confirmationButtonTrigger}[disabled]`,
        isCheck: true,
        in_modal: true,
    };
}
