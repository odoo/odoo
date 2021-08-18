odoo.define('flexipharmacy.CloseSessionPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    var framework = require('web.framework');

    class CloseSessionPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }
        closePos(){
            framework.redirect('/web/session/logout');
        }
    }

    CloseSessionPopup.template = 'CloseSessionPopup';

    Registries.Component.add(CloseSessionPopup);

    return CloseSessionPopup;
});
