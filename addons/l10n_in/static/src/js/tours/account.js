odoo.define('l10n_in.account_tour', function (require) {
"use strict";

require('account.tour');
var core = require('web.core');
let session = require('web.session');
let tour = require('web_tour.tour');

var _t = core._t;

if (session.company_account_fiscal_country_code === 'IN') {
    // Set the GST Treatment
    const stepToAdd = {
        trigger: "select[name=l10n_in_gst_treatment]",
        extra_trigger: "body:not(.modal-open)",
        position: "bottom",
        content: "Set the GST Treatment",
        in_modal: false,
        run: 'text "consumer"',
    };
    const accountTour = tour.tours.account_tour;
    const addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'div[name=invoice_line_ids] .o_field_x2many_list_row_add a:not([data-context])');
    accountTour.steps.splice(addIndex, 0, stepToAdd);
}
});
