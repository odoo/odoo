odoo.define("website_sale.tour_utils", function (require) {
    "use strict";

    const core = require("web.core");
    const _t = core._t;
    const wTourUtils = require('website.tour_utils');

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
            content: "Next",
            trigger: '.oe_cart .btn:contains("Next")',
        });
        return steps;
    }

    function goToCart({quantity = 1, position = "bottom", backend = false} = {}) {
        return {
            content: _t("Go to cart"),
            trigger: `${backend ? "iframe" : ""} a:has(.my_cart_quantity:containsExact(${quantity}))`,
            position: position,
            run: "click",
        };
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

    return {
        addToCart,
        assertCartContains,
        assertProductPrice,
        fillAdressForm,
        goToCart,
        selectPriceList,
        searchProduct,
    };
});
