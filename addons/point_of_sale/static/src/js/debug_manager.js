odoo.define('point_of_sale.DebugManager.Backend', function(require) {
    'use strict';

    const { _t } = require('web.core');
    const DebugManager = require('web.DebugManager.Backend');

    DebugManager.include({
        /**
         * Runs the JS (desktop) tests
         */
        perform_pos_js_tests() {
            this.do_action({
                name: _t('JS Tests'),
                target: 'new',
                type: 'ir.actions.act_url',
                url: '/pos/ui/tests?mod=*',
            });
        },
    });
});
