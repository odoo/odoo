odoo.define('web.company_autocomplete', function (require) {
"use strict";

const AbstractWebClient = require('web.AbstractWebClient');
const session = require('web.session');

return AbstractWebClient.include({

    start: function () {
        if (session.iap_company_enrich) {
            const current_company_id = session.user_companies.current_company;
            this._rpc({
                model: 'res.company',
                method: 'iap_enrich_auto',
                args: [current_company_id],
            }, {
                shadow: true,
            });
        }

        return this._super.apply(this, arguments);
    },

});

});
