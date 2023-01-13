odoo.define('l10n_ar_website_sale.website_sale_tour', function (require) {
"use strict";

require('website_sale_tour.tour');
let tour = require('web_tour.tour');

let website_sale_tour = tour.tours.website_sale_tour;

if (website_sale_tour.extra && (website_sale_tour.extra.company_account_fiscal_country_code || "") === 'AR') {
    // Extend run function to add the AFIP Responsibility
    const websiteSaleTour = tour.tours.website_sale_tour;
    const stepIndex = websiteSaleTour.steps.findIndex(({trigger, content}) => trigger === 'select[name="country_id"]' && content === 'Fulfill billing address form');
    const run = website_sale_tour.steps[stepIndex].run;
    const new_run = function () {
        run();
        $('select[name="l10n_ar_afip_responsibility_type_id"] option').filter(function () {
            return $(this).html().trim() === "Consumidor Final";
        }).attr('selected', true);
        $('select[name="l10n_latam_identification_type_id"] option').filter(function () {
            return $(this).html().trim() === "Foreign ID";
        }).attr('selected', true);
        $('input[name="vat"]').val('12345678-9');
    };
    websiteSaleTour.steps[stepIndex].run = new_run;
}
});
