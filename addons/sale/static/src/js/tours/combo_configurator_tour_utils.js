import { queryAll, queryValue, waitUntil } from '@odoo/hoot-dom';

function comboSelector(comboName) {
    return `
        .sale-combo-configurator-dialog
        [name="sale_combo_configurator_title"]:contains("${comboName}")
    `;
}

function comboItemSelector(comboItemName, extraClasses=[]) {
    const extraClassesSelector = extraClasses.map(extraClass => `.${extraClass}`).join('');
    return `
        .sale-combo-configurator-dialog
        .combo-item-grid
        .product-card${extraClassesSelector}:has(.card-title:contains("${comboItemName}"))
    `;
}

function assertComboCount(count) {
    return {
        content: `Assert that there are ${count} combos`,
        trigger:'.sale-combo-configurator-dialog',
        run: () => queryAll(
            '.sale-combo-configurator-dialog [name="sale_combo_configurator_title"]'
        ).length === count,
    };
}

function assertComboItemCount(comboName, count) {
    return {
        content: `Assert that there are ${count} combo items in combo ${comboName}`,
        trigger: comboSelector(comboName),
        run: () => queryAll(
            `${comboSelector(comboName)} .combo-item-grid .product-card`
        ).length === count,
    };
}

function selectComboItem(comboItemName) {
    return {
        content: `Select combo item ${comboItemName}`,
        trigger: comboItemSelector(comboItemName),
        run: 'click',
    };
}

function assertComboItemSelected(comboItemName) {
    return {
        content: `Assert that combo item ${comboItemName} is selected`,
        trigger: comboItemSelector(comboItemName, ['selected']),
    };
}

function increaseQuantity() {
    return {
        content: "Increase the combo quantity",
        trigger: '.sale-combo-configurator-dialog button[name="sale_quantity_button_plus"]',
        run: 'click',
    };
}

function decreaseQuantity() {
    return {
        content: "Decrease the combo quantity",
        trigger: '.sale-combo-configurator-dialog button[name="sale_quantity_button_minus"]',
        run: 'click',
    };
}

function setQuantity(quantity) {
    return {
        content: `Set the combo quantity to ${quantity}`,
        trigger: '.sale-combo-configurator-dialog input[name="sale_quantity"]',
        run: `edit ${quantity} && click .modal-body`,
    };
}

function assertQuantity(quantity) {
    const quantitySelector = '.sale-combo-configurator-dialog input[name="sale_quantity"]';
    return {
        content: `Assert that the combo quantity is ${quantity}`,
        trigger: quantitySelector,
        run: async () =>
            await waitUntil(() => queryValue(quantitySelector) === quantity, { timeout: 1000 }),
    };
}

function assertPrice(price) {
    return {
        content: `Assert that the price is ${price}`,
        trigger: `
            .sale-combo-configurator-dialog
            [name="sale_combo_configurator_total"]:contains("${price}")
        `,
    };
}

function assertPriceInfo(priceInfo) {
    return {
        content: `Assert that the price info is ${priceInfo}`,
        trigger: `.sale-combo-configurator-dialog footer.modal-footer:contains("${priceInfo}")`,
    };
}

function assertFooterButtonsDisabled() {
    return {
        content: "Assert that the footer buttons are disabled",
        trigger: '.sale-combo-configurator-dialog footer.modal-footer button:disabled',
    };
}

function assertFooterButtonsEnabled() {
    return {
        content: "Assert that the footer buttons are enabled",
        trigger: '.sale-combo-configurator-dialog footer.modal-footer button:enabled',
    };
}

function assertConfirmButtonDisabled() {
    return {
        content: "Assert that the confirm button is disabled",
        trigger: `
            .sale-combo-configurator-dialog
            button[name="sale_combo_configurator_confirm_button"]:disabled
        `,
    };
}

function assertConfirmButtonEnabled() {
    return {
        content: "Assert that the confirm button is enabled",
        trigger: `
            .sale-combo-configurator-dialog
            button[name="sale_combo_configurator_confirm_button"]:enabled
        `,
    };
}

function saveConfigurator() {
    return [
        {
            content: "Confirm the combo configurator",
            trigger: `
                .sale-combo-configurator-dialog
                button[name="sale_combo_configurator_confirm_button"]
            `,
            run: 'click',
        }, {
            content: "Wait until the modal is closed",
            trigger: 'body:not(:has(.modal))',
        },
    ];
}

export default {
    comboSelector,
    comboItemSelector,
    assertComboCount,
    assertComboItemCount,
    selectComboItem,
    assertComboItemSelected,
    increaseQuantity,
    decreaseQuantity,
    setQuantity,
    assertQuantity,
    assertPrice,
    assertPriceInfo,
    assertFooterButtonsDisabled,
    assertFooterButtonsEnabled,
    assertConfirmButtonDisabled,
    assertConfirmButtonEnabled,
    saveConfigurator,
};
