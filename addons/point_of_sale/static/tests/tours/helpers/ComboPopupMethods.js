/** @odoo-module */

const popup = ".popup.combo-configurator-popup";
const productTrigger = (productName) =>
    `label.combo-line:has(article.product .product-name:contains("${productName}"))`;
const isNot = (trigger) => `body:not(:has(${trigger}))`;
const isComboSelectedTrigger = (productName) => `input:checked ~ ${productTrigger(productName)}`;
const confirmationButtonTrigger = `${popup} footer button.confirm`;

export const combo = {
    isPopupShown: () => ({
        content: "Check if the combo popup is shown",
        trigger: popup,
        isCheck: true,
    }),
    select: (productName) => ({
        content: `Select combo item ${productName}`,
        trigger: productTrigger(productName),
    }),
    isSelected: (productName) => ({
        content: `Check that ${productName} is selected`,
        trigger: isComboSelectedTrigger(productName),
        isCheck: true,
    }),
    isNotSelected: (productName) => ({
        content: `Check that ${productName} is not selected`,
        trigger: isNot(isComboSelectedTrigger(productName)),
        isCheck: true,
    }),
    isConfirmationButtonDisabled: () => ({
        content: "try to click `confirm` without having made all the selections",
        trigger: `${confirmationButtonTrigger}[disabled]`,
        isCheck: true,
    }),
    confirm: () => ({
        content: "Click `confirm`",
        trigger: confirmationButtonTrigger,
    }),
};
