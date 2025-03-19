/** @odoo-module alias=l10n_it_edi_website_sale.tour **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_checkout_address', {
    test: true,
    url: '/shop',
    steps: () => [
        {
            content: "search Storage Box",
            trigger: 'form input[name="search"]',
            run: "text Storage Box",
        },
        {
            content: "search Storage Box",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "select Storage Box",
            trigger: '.oe_product_cart:first a:contains("Storage Box")',
        },
        {
            id: 'add_cart_step',
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
            tourUtils.goToCart(),
        {
            content: "go to address form",
            trigger: 'a[href="/shop/checkout?express=1"]',
        },
        // check if the fields Codice Fiscale and PA index are present
        {
            content: "check if the fields Codice Destinatario is present",
            trigger: 'input[name="l10n_it_pa_index"]',
            run: "text 1234567890123456789012345",
        },
        {
            content: "check if the fields Codice Fiscale is present",
            trigger: 'input[name="l10n_it_codice_fiscale"]',
            run: "text 12345678901",
        },
    ]
});

registry.category("web_tour.tours").add('shop_checkout_address_create_partner', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "Storage Box" }),
        tourUtils.goToCart(),
        {
            content: "go to address form",
            trigger: 'a[href="/shop/checkout?express=1"]',
        },
        {
            content: "Fill address form with VAT",
            trigger: 'select[name="country_id"]',
            run: function () {
                $('input[name="name"]').val('abc');
                $('input[name="phone"]').val('99999999');
                $('input[name="email"]').val('abc@odoo.com');
                $('input[name="vat"]').val('IT12345670017');
                $('input[name="street"]').val('SO1 Billing Street, 33');
                $('input[name="city"]').val('SO1BillingCity');
                $('input[name="zip"]').val('10000');
            },
        },
        {
            content: "Select country with code 'IT' to trigger compute of Codice Fiscale",
            trigger: "select[name='country_id']",
            run: function () {
                const countrySelect = $("select[name='country_id']");
                countrySelect.find('option[code="IT"]').attr('selected', true);
                countrySelect.trigger('change');
            }
        },
        {
            content: "Check if the Codice Fiscale value matches",
            trigger: "input[name='l10n_it_codice_fiscale']",
            run: function () {
                if ($("input[name='l10n_it_codice_fiscale']").val() !== "12345670017") {
                    console.error('Expected "12345670017" for Codice Fiscale.');
                }
            }
        },
        {
            content: "Add state",
            trigger: 'select[name="state_id"]',
            run: function () {
                $('#state_id option:contains(Cremona)').attr('selected', true);
            },
        },
        {
            content: "Click on next button",
            trigger: '.oe_cart .btn:contains("Continue checkout")',
        },
        {
            content: "Check selected billing address is same as typed in previous step",
            trigger: '#shipping_and_billing:contains(SO1 Billing Street, 33):contains(SO1BillingCity)',
            run: function () {}, // it's a check
        },
]});
