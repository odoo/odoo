odoo.define('l10n_ar.account_tour', function (require) {
"use strict";

require('account.tour');
let session = require('web.session');
let tour = require('web_tour.tour');

if (session.company_account_fiscal_country_code === 'AR') {
    const stepsToAdd = [
    // Configure the AFIP Responsibility
    {
        trigger: "div[name=l10n_ar_afip_responsibility_type_id] input",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        position: "bottom",
        content: "Set the AFIP Responsability",
        run: "text IVA",
    }, {
        trigger: ".ui-menu-item > a:contains('IVA').ui-state-active",
        auto: true,
        in_modal: false,
    }];
    const accountTour = tour.tours.account_tour;
    const addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'div[name=partner_id] input');
    accountTour.steps.splice(addIndex + 2, 0, ...stepsToAdd);
}
});
