/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { clickOnElement } from '@website/js/tours/tour_utils';

export function addToCart({
    productName,
    search = true,
    productHasVariants = false,
    expectUnloadPage = false,
} = {}) {
    const steps = [];
    if (search) {
        steps.push(...searchProduct(productName));
    }
    steps.push({
        content: productName,
        trigger: `a:contains(${productName})`,
        run: "click",
        expectUnloadPage,
    });
    steps.push({
        content: "Add to cart",
        trigger: "#add_to_cart",
        run: "click",
    });
    if (productHasVariants) {
        steps.push(clickOnElement('Continue Shopping', 'button:contains("Continue Shopping")'));
    }
    return steps;
}

export function assertCartAmounts({taxes = false, untaxed = false, total = false, delivery = false}) {
    let steps = [];
    if (taxes) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_total_taxes .oe_currency_value:contains(/^${taxes}$/)`,
        });
    }
    if (untaxed) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_total_untaxed .oe_currency_value:contains(/^${untaxed}$/)`,
        });
    }
    if (total) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_total .oe_currency_value:contains(/^${total}$/)`,
        });
    }
    if (delivery) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_delivery .oe_currency_value:contains(/^${delivery}$/)`,
        });
    }
    return steps
}

export function assertCartContains({productName, backend, notContains = false} = {}) {
    let trigger = `a:contains(${productName})`;

    if (notContains) {
        trigger = `:not(${trigger})`;
    }
    return {
        content: `Checking if ${productName} is in the cart`,
        trigger: `${backend ? ":iframe" : ""} ${trigger}`,
    };
}

/**
 * Used to assert if the price attribute of a given product is correct on the /shop view
 */
export function assertProductPrice(attribute, value, productName) {
    return {
        content: `The ${attribute} of the ${productName} is ${value}`,
        trigger: `div:contains("${productName}") [data-oe-expression="template_price_vals['${attribute}']"] .oe_currency_value:contains("${value}")`,
    };
}

export function fillAdressForm(
    adressParams = {
        name: "John Doe",
        phone: "123456789",
        email: "johndoe@gmail.com",
        street: "1 rue de la paix",
        city: "Paris",
        zip: "75000",
    },
    expectUnloadPage = false
) {
    const steps = [];
    steps.push({
        trigger: "#o_country_id",
        run: "selectByLabel Belgium",
    });
    for (const arg of ["name", "phone", "email", "street", "city", "zip"]) {
        steps.push({
            content: `Address filling ${arg}`,
            trigger: `form.checkout_autoformat input[name=${arg}]`,
            run: `edit ${adressParams[arg]}`,
        });
    }
    steps.push({
        content: "Continue checkout",
        trigger: "#save_address",
        run: "click",
        expectUnloadPage,
    });
    return steps;
}

export function goToCart({
    quantity = 1,
    position = "bottom",
    backend = false,
    expectUnloadPage = true,
} = {}) {
    return {
        content: _t("Go to cart"),
        trigger: `${backend ? ":iframe" : ""} a sup.my_cart_quantity:contains(/^${quantity}$/)`,
        tooltipPosition: position,
        run: "click",
        expectUnloadPage,
    };
}

export function goToCheckout() {
    return {
        content: 'Checkout your order',
        trigger: 'a[href^="/shop/checkout"]',
        run: 'click',
        expectUnloadPage: true,
    };
}

export function confirmOrder() {
    return {
        content: 'Confirm',
        trigger: 'a[href^="/shop/confirm_order"]',
        run: 'click',
        expectUnloadPage: true,
    };
}

export function pay({ expectUnloadPage = false, waitFinalizeYourPayment = false } = {}) {
    const steps = [
        {
            content: 'Pay',
            //Either there are multiple payment methods, and one is checked, either there is only one, and therefore there are no radio inputs
            trigger: 'button[name="o_payment_submit_button"]',
            run: "click",
            expectUnloadPage,
        },
    ];
    if (waitFinalizeYourPayment) {
        steps.push({
            trigger: "h1:contains(finalize your payment)",
            expectUnloadPage: true,
        });
    }
    return steps;
}

export function payWithDemo() {
    return [{
        content: 'eCommerce: select Test payment provider',
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="demo"]',
        run: "click",
    }, {
        content: 'eCommerce: add card number',
        trigger: 'input[name="customer_input"]',
        run: "edit 4242424242424242",
    },
    ...pay(),
    {
        content: 'eCommerce: check that the payment is successful',
        trigger: '.oe_website_sale_tx_status:contains("Your payment has been successfully processed.")',
    }]
}

export function payWithTransfer({
    redirect = false,
    expectUnloadPage = false,
    waitFinalizeYourPayment = false,
} = {}) {
    const first_step = {
        content: "Select `Wire Transfer` payment method",
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
        run: "click",
    }
    if (!redirect) {
        return [
            first_step,
            ...pay({ expectUnloadPage, waitFinalizeYourPayment }),
            {
                content: "Last step",
                trigger:
                    '.oe_website_sale_tx_status:contains("Please use the following transfer details")',
                timeout: 30000,
            },
        ];
    } else {
        return [
            first_step,
            ...pay({ expectUnloadPage, waitFinalizeYourPayment }),
            {
                content: "Last step",
                trigger:
                    '.oe_website_sale_tx_status:contains("Please use the following transfer details")',
                timeout: 30000,
                run() {
                    window.location.href = '/contactus'; // Redirect in JS to avoid the RPC loop (20x1sec)
                },
                expectUnloadPage: true,
            },
            {
                content: "wait page loaded",
                trigger: 'h1:contains("Contact us")',
            },
        ];
    }
}

export function searchProduct(productName, { select = false } = {}) {
    const steps = [
        {
            content: "Search for the product",
            trigger: 'form input[name="search"]',
            run: `edit ${productName}`,
        },
        {
            content: `Search ${productName}`,
            trigger: `form:has(input[name="search"]) .oe_search_button`,
            run: "click",
            expectUnloadPage: true,
        },
    ];
    if (select) {
        steps.push({
            content: `Select ${productName}`,
            trigger: `.oe_product_cart:first a:contains(/^${productName}$/i)`,
            run: "click",
            expectUnloadPage: true,
        });
    }
    return steps;
}

/**
 * Used to select a pricelist on the /shop view
 */
export function selectPriceList(pricelist) {
    return [
        {
            content: "Click on pricelist dropdown",
            trigger: "div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
            run: "click",
        },
        {
            content: "Click on pricelist",
            trigger: `span:contains(${pricelist})`,
            run: "click",
            expectUnloadPage: true,
        },
    ];
}
