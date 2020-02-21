odoo.define('point_of_sale.test_setup_pos', async function(require) {
    'use strict';

    /**
     * We setup here the PosModel instance that will be used for testing.
     * It might be needed in different parts of testing.
     */

    const env = require('web.env');
    const { PosModel } = require('point_of_sale.models');

    Object.assign(env.session, {
        uid: 2,
        user_context: {
            lang: 'en_US',
            tz: 'Europe/Brussels',
            allowed_company_ids: [1],
        },
    });

    let posContainer = {};

    QUnit.module('Initialize PosModel', {
        async before() {
            posContainer.pos = new PosModel({
                rpc: env.services.rpc,
                session: env.session,
                do_action: async () => {},
                loading_message: () => {},
                loading_progress: () => {},
                loading_skip: () => {},
            });
            await posContainer.pos.ready;
            this.pos = posContainer.pos;
            console.log('PosModel instance successfully created.')
            // TODO jcb: setup the mock after loading the PosModel instance.
        },
    });

    QUnit.test('check if PosModel is instantiated', async function(assert) {
        assert.expect(1);
        assert.strictEqual(this.pos === posContainer.pos, true);
    });

    return posContainer;
});
