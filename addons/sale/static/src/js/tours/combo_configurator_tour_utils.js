import { queryAll } from '@odoo/hoot-dom';

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
        .product-card${extraClassesSelector}:has(h6:contains("${comboItemName}"))
    `;
}

function assertComboCount(count) {
    return {
        content: `Assert that there are ${count} combos`,
        trigger: '.sale-combo-configurator-dialog',
        run() {
            const selector = `.sale-combo-configurator-dialog [name="sale_combo_configurator_title"]`;
            if (queryAll(selector).length !== count) {
                console.error(`Assertion failed`);
            }
        },
    };
}

function assertComboItemCount(comboName, count) {
    return {
        content: `Assert that there are ${count} combo items in combo ${comboName}`,
        trigger: comboSelector(comboName),
        run() {
            const selector = `${comboSelector(comboName)} + .row .product-card`;
            if (queryAll(selector).length !== count) {
                console.error(`Assertion failed`);
            }
        },
    };
}

function assertSelectedComboItemCount(count) {
    return {
        content: `Assert that there are ${count} selected combo items`,
        trigger: '.sale-combo-configurator-dialog',
        run() {
            const selector = `.sale-combo-configurator-dialog .row .product-card.selected`;
            if (queryAll(selector).length !== count) {
                console.error(`Assertion failed`);
            }
        },
    };
}

function assertPreselectedComboItemCount(count) {
    return {
        content: `Assert that there are ${count} preselected combo items`,
        trigger: '.sale-combo-configurator-dialog',
        run() {
            const selector = '.sale-combo-configurator-dialog div[name="preselected_product_name"]';
            if (queryAll(selector).length !== count) {
                console.error(`Assertion failed`);
            }
        },
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

function assertComboItemPreselected(comboItemName) {
    return {
        content: `Assert that combo item ${comboItemName} is preselected`,
        trigger: `[name="preselected_product_name"]:contains(${comboItemName})`,
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
    return {
        content: `Assert that the combo quantity is ${quantity}`,
        trigger: `.sale-combo-configurator-dialog input[name="sale_quantity"]:value(${quantity})`,
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
            trigger: 'body:not(:has(.sale-combo-configurator-dialog))',
        },
    ];
}

export default {
    comboSelector,
    comboItemSelector,
    assertComboCount,
    assertComboItemCount,
    assertSelectedComboItemCount,
    assertPreselectedComboItemCount,
    selectComboItem,
    assertComboItemSelected,
    assertComboItemPreselected,
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
