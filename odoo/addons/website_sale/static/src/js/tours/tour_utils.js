/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import wTourUtils from "@website/js/tours/tour_utils";

function addToCart({productName, search = true, productHasVariants = false}) {
    const steps = [];
    if (search) {
        steps.push(...searchProduct(productName));
    }
    steps.push(wTourUtils.clickOnElement(productName, `a:contains(${productName})`));
    steps.push(wTourUtils.clickOnElement('Add to cart', '#add_to_cart'));
    if (productHasVariants) {
        steps.push(wTourUtils.clickOnElement('Continue Shopping', 'button:contains("Continue Shopping")'));
    }
    return steps;
}

function assertCartAmounts({taxes = false, untaxed = false, total = false, delivery = false}) {
    let steps = [];
    if (taxes) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_total_taxes .oe_currency_value:containsExact(${taxes})`,
            run: function () {},  // it's a check
        });
    }
    if (untaxed) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_total_untaxed .oe_currency_value:containsExact(${untaxed})`,
            run: function () {},  // it's a check
        });
    }
    if (total) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_total .oe_currency_value:containsExact(${total})`,
            run: function () {},  // it's a check
        });
    }
    if (delivery) {
        steps.push({
            content: 'Check if the tax is correct',
            trigger: `tr#order_delivery .oe_currency_value:containsExact(${delivery})`,
            run: function () {},  // it's a check
        });
    }
    return steps
}

function assertCartContains({productName, backend, notContains = false} = {}) {
    let trigger = `a:contains(${productName})`;

    if (notContains) {
        trigger = `:not(${trigger})`;
    }
    return {
        content: `Checking if ${productName} is in the cart`,
        trigger: `${backend ? "iframe" : ""} ${trigger}`,
        run: () => {}
    };
}

/**
 * Used to assert if the price attribute of a given product is correct on the /shop view
 */
function assertProductPrice(attribute, value, productName) {
    return {
        content: `The ${attribute} of the ${productName} is ${value}`,
        trigger: `div:contains("${productName}") [data-oe-expression="template_price_vals['${attribute}']"] .oe_currency_value:contains("${value}")`,
        run: () => {}
    };
}

function fillAdressForm(adressParams = {
    name: "John Doe",
    phone: "123456789",
    email: "johndoe@gmail.com",
    street: "1 rue de la paix",
    city: "Paris",
    zip: "75000"
}) {
    let steps = [];
    steps.push({
        content: "Address filling",
        trigger: 'select[name="country_id"]',
        run: () => {
            $('input[name="name"]').val(adressParams.name);
            $('input[name="phone"]').val(adressParams.phone);
            $('input[name="email"]').val(adressParams.email);
            $('input[name="street"]').val(adressParams.street);
            $('input[name="city"]').val(adressParams.city);
            $('input[name="zip"]').val(adressParams.zip);
            $('#country_id option:eq(1)').attr('selected', true);
        }
    });
    steps.push({
        content: "Continue checkout",
        trigger: '.oe_cart .btn:contains("Continue checkout")',
    });
    return steps;
}

function goToCart({quantity = 1, position = "bottom", backend = false} = {}) {
    return {
        content: _t("Go to cart"),
        trigger: `${backend ? "iframe" : ""} a sup.my_cart_quantity:containsExact(${quantity})`,
        position: position,
        run: "click",
    };
}

function goToCheckout() {
    return {
        content: 'Checkout your order',
        trigger: 'a[href^="/shop/checkout"]',
        run: 'click',
    };
}

function pay() {
    return {
        content: 'Pay',
        //Either there are multiple payment methods, and one is checked, either there is only one, and therefore there are no radio inputs
        // extra_trigger: '#payment_method input:checked,#payment_method:not(:has("input:radio:visible"))',
        trigger: 'button[name="o_payment_submit_button"]:visible:not(:disabled)'
    };
}

function payWithDemo() {
    return [{
        content: 'eCommerce: select Test payment provider',
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="demo"]'
    }, {
        content: 'eCommerce: add card number',
        trigger: 'input[name="customer_input"]',
        run: 'text 4242424242424242'
    },
    pay(),
    {
        content: 'eCommerce: check that the payment is successful',
        trigger: '.oe_website_sale_tx_status:contains("Your payment has been successfully processed.")',
        run: function () {}
    }]
}

function payWithTransfer(redirect=false) {
    const first_step = {
        content: "Select `Wire Transfer` payment method",
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
    }
    if (!redirect) {
        return [
        first_step,
        pay(),
        {
            content: "Last step",
            trigger: '.oe_website_sale_tx_status:contains("Please use the following transfer details")',
            timeout: 30000,
            isCheck: true,
        }]
    } else {
        return [
            first_step,
            pay(),
            {
                content: "Last step",
                trigger: '.oe_website_sale_tx_status:contains("Please use the following transfer details")',
                timeout: 30000,
                run: () => {
                    window.location.href = '/contactus'; // Redirect in JS to avoid the RPC loop (20x1sec)
                },
            }, {
                content: "wait page loaded",
                trigger: 'h1:contains("Contact us")',
                run: function () {}, // it's a check
            }
        ]
    }
}

function searchProduct(productName) {
    return [
        wTourUtils.clickOnElement('Shop', 'a:contains("Shop")'),
        {
            content: "Search for the product",
            trigger: 'form input[name="search"]',
            run: `text ${productName}`
        },
        wTourUtils.clickOnElement('Search', 'form:has(input[name="search"]) .oe_search_button'),
    ];
}

/**
 * Used to select a pricelist on the /shop view
 */
function selectPriceList(pricelist) {
    return [
        {
            content: "Click on pricelist dropdown",
            trigger: "div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
        },
        {
            content: "Click on pricelist",
            trigger: `span:contains(${pricelist})`,
        },
    ];
}

export default {
    addToCart,
    assertCartAmounts,
    assertCartContains,
    assertProductPrice,
    fillAdressForm,
    goToCart,
    goToCheckout,
    pay,
    payWithDemo,
    payWithTransfer,
    selectPriceList,
    searchProduct,
};
