odoo.define('payment.tour', function(require) {
    "use strict";

    var core = require('web.core');
    var tour = require('web_tour.tour');

    var _t = core._t;

    tour.register('payment_tour', {
        'skip_enabled': true,
    }, [{
        trigger: ".oe_status",
        content: _t("Once your setup is ready, set your credentials for production mode and activate it."),
        position: "right"
    }, ]);

});
