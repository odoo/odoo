/* global posmodel */

export function clickBtn(buttonName) {
    return {
        content: `Click on button '${buttonName}'`,
        trigger: `.btn:contains('${buttonName}')`,
        run: "click",
    };
}

export function negate(selector, parent = "body") {
    return `${parent}:not(:has(${selector}))`;
}

export function negateStep(step) {
    return {
        ...step,
        content: `Check that: ---${step.content}--- is not true`,
        trigger: negate(step.trigger),
    };
}

export function checkBtn(buttonName) {
    return {
        content: `Check is button '${buttonName}'`,
        trigger: `.btn:contains('${buttonName}')`,
    };
}

export function checkIsNoBtn(buttonName) {
    return {
        content: `Check that '${buttonName}' do not exist`,
        trigger: `body:not(:has(.btn:text(${buttonName})))`,
    };
}

export function checkIsDisabledBtn(buttonName) {
    return {
        content: `Check if button '${buttonName}' is disabled`,
        trigger: `button.disabled:contains("${buttonName}")`,
    };
}

export function openLanguageSelector() {
    return {
        content: `Click on language selector`,
        trigger: `.o_self_language_selector`,
        run: "click",
    };
}

export function changeLanguage(language) {
    return [
        openLanguageSelector(),
        {
            content: `Check that the language is available`,
            trigger: `.self_order_language_popup .btn:contains(${language})`,
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: `Check that the language changed`,
            trigger: `.o_self_language_selector:contains(${language})`,
        },
    ];
}

export function clickBackBtn() {
    return {
        content: `Click back button`,
        trigger: `.btn.btn-back`,
        run: "click",
    };
}

export function checkQRCodeGenerated() {
    return {
        content: `Check that the QR code is shown`,
        trigger: "h1:contains('Scan the QR code to pay')",
    };
}

export function increaseComboItemQty(productName, qty) {
    const steps = [
        {
            content: `Check product name`,
            trigger: `.combo_product_box span:contains("${productName}")`,
        },
    ];

    for (let i = 1; i < qty; i++) {
        steps.push(
            {
                content: `Verify the quantity of "${productName}" is updated to ${i}.`,
                trigger: `.item_qty_container .o-so-tabular-nums:contains("${i}")`,
            },
            {
                content: `Increase the quantity of "${productName}" by clicking the "+" button.`,
                trigger: `.item_qty_container button:eq(1)`,
                run: "click",
            }
        );
    }

    return steps;
}

export function setProductAvailability(productName, value) {
    return {
        content: `Set 'self_order_available' of product '${productName}' to ${value}`,
        trigger: "body",
        run: async function () {
            const product = posmodel.data.models["product.template"].find(
                (p) => p.name === productName
            );
            if (!product) {
                throw new Error(`Product '${productName}' not found.`);
            }
            product.self_order_available = value;
        },
    };
}

export function checkMissingRequiredsExists() {
    return {
        content: "Redirecting component is available for handling missing details",
        trigger: "div.missing_required_details",
    };
}

export function clickMissingRequireds() {
    return {
        content: "Click on missing required details button",
        trigger: "div.missing_required_details button",
        run: "click",
    };
}
