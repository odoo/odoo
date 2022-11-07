odoo.define('l10n_cl.account_tour', function (require) {
"use strict";

require('account.tour');
let session = require('web.session');
let tour = require('web_tour.tour');

if (session.company_account_fiscal_country_code === 'CL') {
    const stepsToAdd = [
    // Configure the partner country
    {
        trigger: "div[name=country_id] input",
        position: "bottom",
        content: "Select a country for the partner",
        run: "text Chile",
    }, {
        trigger: ".ui-menu-item > a:contains('Chile').ui-state-active",
        auto: true,
        in_modal: false,
    },
    // Configure the Identification Type and Number
    {
        trigger: "div[name=l10n_latam_identification_type_id] input",
        position: "bottom",
        content: "Set the Identification Type",
        run: "text Foreign ID",
    }, {
        trigger: ".ui-menu-item > a:contains('Foreign ID').ui-state-active",
        auto: true,
        in_modal: false,
    }, {
        trigger: "input[name=vat]",
        position: "bottom",
        content: "Set the Identification Number",
        run: "text 12345678-9",
    },
    // Configure the Taxpayer Type
    {
        trigger: "select[name=l10n_cl_sii_taxpayer_type]",
        position: "bottom",
        content: "Set the Taxpayer Type",
        run: 'text "3"',
    }];
    const accountTour = tour.tours.account_tour;
    const addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'div[name=partner_id] input');
    accountTour.steps.splice(addIndex + 2, 0, ...stepsToAdd);
}
});
