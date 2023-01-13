odoo.define('l10n_ar_website_sale.shop_buy_product_tour', function (require) {
"use strict";

require('website_sale.tour');
let session = require('web.session');
let tour = require('web_tour.tour');

if (session.company_account_fiscal_country_code === 'AR') {
    const stepsToAdd = [
    // Configure the AFIP Responsibility
    {
        content: "Fulfill shipping address form",
        trigger: 'select[name="country_id"]',
        run: function () {
            $('select[name="l10n_ar_afip_responsibility_type_id"] option').filter(function () {
                return $(this).html().trim() === "Consumidor Final";
            }).attr('selected', true);
            $('select[name="l10n_latam_identification_type_id"] option').filter(function () {
                return $(this).html().trim() === "Foreign ID";
            }).attr('selected', true);
            $('input[name="vat"]').val('12345678-9');
        },
    }, {
        content: "Click on Next button",
        trigger: '.oe_cart .btn:contains("Next")',
    }, {
        content: "Click on Confirm button",
        trigger: '.oe_cart .btn:contains("Confirm")',
    }];

    const shopBuyProductTour = tour.tours.shop_buy_product;
    const addIndex = shopBuyProductTour.steps.findIndex(({trigger}) => trigger === 'a[href*="/shop/checkout"]');
    shopBuyProductTour.steps.splice(addIndex + 1, 0, ...stepsToAdd);
}
});
