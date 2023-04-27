odoo.define('l10n_ar_website_sale.website_sale_tour', function (require) {
"use strict";

    let tour = require('web_tour.tour');

    let website_sale_tour = tour.tours.website_sale_tour;
    // Remove the step related to other localisations
    website_sale_tour.steps = _.filter(website_sale_tour.steps, step => !step.l10n || step.l10n === "ar");

    let address_step = _.findIndex(website_sale_tour.steps, step => step.content === 'Fulfill billing address form');
    let step_run = website_sale_tour.steps[address_step].run;

    website_sale_tour.steps[address_step].run = function () {
        step_run();
        $("select[name='l10n_ar_afip_responsibility_type_id'] option[value='5']").prop('selected', true);
        $("select[name='l10n_latam_identification_type_id'] option[value='1']").prop('selected', true);
        $("input[name='vat']").val('123456789');
    };
});
