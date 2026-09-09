/** @odoo-module native */
import { _t } from "@web/core/translation";
import { clickOnElement } from "@website/js/tours/tour_utils";

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
        steps.push(
            clickOnElement("Continue Shopping", 'button:contains("Continue Shopping")'),
        );
    }
    return steps;
}

export function assertCartAmounts({
    taxes = false,
    untaxed = false,
    total = false,
    delivery = false,
}) {
    let steps = [];
    if (taxes) {
        steps.push({
            content: "Check if the tax is correct",
            trigger: `tr[name="o_order_total_taxes"] .oe_currency_value:text(${taxes})`,
        });
    }
    if (untaxed) {
        steps.push({
            content: "Check if the subtotal is correct",
            trigger: `tr[name="o_order_total_untaxed"] .oe_currency_value:text(${untaxed})`,
        });
    }
    if (total) {
        steps.push({
            content: "Check if the total is correct",
            trigger: `tr[name="o_order_total"] .oe_currency_value:text(${total})`,
        });
    }
    if (delivery) {
        steps.push({
            content: "Check if the delivery is correct",
            trigger: `tr[name='o_order_delivery'] .oe_currency_value:text(${delivery})`,
        });
    }
    return steps;
}

export function assertCartContains({
    productName,
    backend,
    notContains = false,
    combinationName = false,
} = {}) {
    let trigger = `h6:contains(${productName})`;

    if (notContains) {
        trigger = `:not(${trigger})`;
    }
    let steps = [
        {
            content: `Checking if ${productName} is in the cart`,
            trigger: `${backend ? ":iframe" : ""} ${trigger}`,
        },
    ];

    if (combinationName) {
        const combination_trigger = `span[class*=h6]:contains(${combinationName})`;
        steps.push({
            content: `Checking if ${combinationName} is the chosen combination in the cart`,
            trigger: `${backend ? ":iframe" : ""} ${combination_trigger}`,
        });
    }

    return steps;
}

/**
 * Asserts the add-to-cart toast notification shows the given product, qty
 * and price (and, optionally, a selected no-variant/custom attribute line).
 */
export function assertToastNotification({ productName, qty, price, combinationName = false }) {
    const steps = [
        {
            content: `check that ${qty} ${productName} was added`,
            trigger: `.toast-body span:contains("${productName}")`,
        },
        {
            content: `check that ${qty} ${productName} was added`,
            trigger: `.toast-body span:contains("${qty}")`,
        },
    ];

    if (combinationName) {
        steps.push({
            content: "check that the novariants/custom attributes are displayed.",
            trigger: `.toast-body span.text-muted.small:contains("${combinationName}")`,
        });
    }

    steps.push({
        content: `check the price of ${qty} ${productName}`,
        trigger: `.toast-body div:contains("${price}")`,
    });

    return steps;
}

/**
 * The `aria-label` each price carries in `product_tile_templates.xml`.
 *
 * This used to select on `data-oe-expression`, which is the template's own
 * source expression -- emitted into every page by `ir.qweb._get_widget`, edit
 * mode or not. That attribute is branding: it now appears only when
 * `inherit_branding` is set, as it already did for `t-field`. The accessibility
 * label is the better hook regardless: it is a contract with the reader, where
 * the expression was an implementation detail of the template.
 */
const PRICE_ARIA_LABELS = {
    price_reduce: "Sale price",
    base_price: "Original price",
};

export function assertProductPrice(attribute, value, productName) {
    const label = PRICE_ARIA_LABELS[attribute];
    if (!label) {
        throw new Error(`assertProductPrice: no aria-label known for "${attribute}"`);
    }
    return {
        content: `The ${attribute} of the ${productName} is ${value}`,
        trigger: `div:contains("${productName}") [aria-label="${label}"] .oe_currency_value:contains("${value}")`,
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
    expectUnloadPage = false,
) {
    const steps = [];
    steps.push({
        trigger: "#o_country_id",
        run: "selectByLabel Belgium",
    });
    for (const arg of ["name", "phone", "email", "street", "city", "zip"]) {
        steps.push({
            content: `Address filling ${arg}`,
            trigger: `form.address_autoformat input[name=${arg}]`,
            run: `edit ${adressParams[arg]}`,
        });
    }
    steps.push({
        content: "Continue checkout",
        trigger: "a[name='website_sale_main_button']",
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
        trigger: `${backend ? ":iframe" : ""} a sup.my_cart_quantity:text(${quantity})`,
        tooltipPosition: position,
        run: "click",
        expectUnloadPage,
    };
}

export function goToCheckout() {
    return {
        content: "Checkout your order",
        trigger: 'a[href^="/shop/checkout"]',
        run: "click",
        expectUnloadPage: true,
    };
}

export function confirmOrder() {
    return {
        content: "Confirm",
        trigger: 'a[href^="/shop/payment"]',
        run: "click",
        expectUnloadPage: true,
    };
}

export function pay({
    expectUnloadPage = false,
    waitFinalizeYourPayment = false,
} = {}) {
    const steps = [
        {
            content: "Pay",
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
    return [
        {
            content: "eCommerce: add card number",
            trigger: 'input[name="customer_input"]',
            run: "edit 4242424242424242",
        },
        ...pay({ expectUnloadPage: true }),
        {
            content: "eCommerce: check that the payment is successful",
            trigger:
                '[name="order_confirmation"]:contains("Your payment has been processed.")',
        },
    ];
}

export function payWithTransfer({
    redirect = false,
    expectUnloadPage = false,
    waitFinalizeYourPayment = false,
} = {}) {
    const first_step = {
        content: "Select `Wire Transfer` payment method",
        trigger:
            'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
        run: "click",
    };
    if (!redirect) {
        return [
            first_step,
            ...pay({ expectUnloadPage, waitFinalizeYourPayment }),
            {
                content: "Last step",
                trigger:
                    '[name="order_confirmation"]:contains("Please use the following transfer details")',
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
                    '[name="order_confirmation"]:contains("Please use the following transfer details")',
                timeout: 30000,
                run() {
                    window.location.href = "/contactus";
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
            trigger: `.oe_product_cart:first a:text(${productName})`,
            run: "click",
            expectUnloadPage: true,
        });
    }
    return steps;
}

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

export function waitForInteractionToLoad() {
    return {
        content: "Wait for interaction to be ready",
        trigger: `body[is-ready=true]`,
    };
}
