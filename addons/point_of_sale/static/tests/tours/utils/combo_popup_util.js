import { negate } from "@point_of_sale/../tests/tours/utils/common";

const productTrigger = (productName) =>
    `label.combo-item article.product:has(.product-name:contains("${productName}"))`;
const isComboSelectedTrigger = (productName) => `input:checked ~ ${productTrigger(productName)}`;
const confirmationButtonTrigger = `footer button.confirm`;

export function select(productName) {
    return {
        content: `Select combo item ${productName}`,
        trigger: `.modal ${productTrigger(productName)}`,
        run: "click",
    };
}
export function isSelected(productName) {
    return {
        content: `Check that ${productName} is selected`,
        trigger: `.modal ${isComboSelectedTrigger(productName)}`,
        run: "click",
    };
}
export function isNotSelected(productName) {
    return {
        content: `Check that ${productName} is not selected`,
        trigger: `.modal ${negate(isComboSelectedTrigger(productName), ".modal-body")}`,
        run: "click",
    };
}
export function isConfirmationButtonDisabled() {
    return {
        content: "try to click `confirm` without having made all the selections",
        trigger: `.modal ${confirmationButtonTrigger}[disabled]`,
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

export function isNotPresent(productName) {
    return {
        content: `Check that ${productName} is not present in the combo options`,
        trigger: negate(productTrigger(productName), ".modal"),
    };
}
