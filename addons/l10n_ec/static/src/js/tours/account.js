odoo.define('l10n_ec.account_tour', function (require) {
"use strict";

require('account.tour');
let session = require('web.session');
let tour = require('web_tour.tour');

if (session.company_account_fiscal_country_code === 'EC') {
    // Configure the Document Number: In case there isn't already a posted invoice,
    // the document number will not be set automaticly and therefore should be manually set.
    const stepToAdd = {
        trigger: "div[name=l10n_latam_document_type_id]",
        auto: true,
        in_modal: false,
        run: function () {
            $('input[name="l10n_latam_document_number"]').val('001-001-123456789').trigger('change');
        }
    };
    const accountTour = tour.tours.account_tour;
    const addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'button[name=action_post]');
    accountTour.steps.splice(addIndex - 1, 0, stepToAdd);
}
});
