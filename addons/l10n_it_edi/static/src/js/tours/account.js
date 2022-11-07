odoo.define('l10n_it_edi.account_tour', function (require) {
"use strict";

require('account.tour');
var core = require('web.core');
let session = require('web.session');
let tour = require('web_tour.tour');

var _t = core._t;

if (session.company_account_fiscal_country_code === 'IT') {
    const stepsToAdd = [
    // Configure the partner address and vat
    {
        trigger: "input[name=street]",
        position: "right",
        content: "Set a Street",
        run: "text Test Street 123",
    }, {
        trigger: "input[name=city]",
        position: "right",
        content: "Set a City",
        run: "text Rome",
    }, {
        trigger: "input[name=zip]",
        position: "right",
        content: "Set a Zip Code",
        run: "text 39020",
    }, {
        trigger: "div[name=country_id] input",
        position: "right",
        content: "Set a country",
        run: "text Italy",
    }, {
        trigger: ".ui-menu-item > a:contains('Italy').ui-state-active",
        auto: true,
        in_modal: false,
    }, {
        trigger: "div[name=vat] input",
        position: "bottom",
        content: "Set a VAT",
        run: "text IT07643520567",
    }];

    const accountTour = tour.tours.account_tour;
    const addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'div[name=partner_id] input');
    accountTour.steps.splice(addIndex + 2, 0, ...stepsToAdd);
}
});
