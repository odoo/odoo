/** @odoo-module */

const popup = ".popup.combo-configurator-popup";
const productTrigger = (productName) =>
    `label.combo-line article.product:has( .product-name:contains("${productName}"))`;
const isNot = (trigger) => `body:not(:has(${trigger}))`;
const isComboSelectedTrigger = (productName) => `input:checked ~ ${productTrigger(productName)}`;
const confirmationButtonTrigger = `${popup} footer button.confirm`;

export function isPopupShown() {
    return {
        content: "Check if the combo popup is shown",
        trigger: popup,
        isCheck: true,
    };
}
export function select(productName) {
    return {
        content: `Select combo item ${productName}`,
        trigger: productTrigger(productName),
    };
}
export function isSelected(productName) {
    return {
        content: `Check that ${productName} is selected`,
        trigger: isComboSelectedTrigger(productName),
        isCheck: true,
    };
}
export function isNotSelected(productName) {
    return {
        content: `Check that ${productName} is not selected`,
        trigger: isNot(isComboSelectedTrigger(productName)),
        isCheck: true,
    };
}
export function isConfirmationButtonDisabled() {
    return {
        content: "try to click `confirm` without having made all the selections",
        trigger: `${confirmationButtonTrigger}[disabled]`,
        isCheck: true,
    };
}
export function confirm() {
    return {
        content: "Click `confirm`",
        trigger: confirmationButtonTrigger,
    };
}
