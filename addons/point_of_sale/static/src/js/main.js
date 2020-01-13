odoo.define('point_of_sale.main', function(require) {
    'use strict';

    const env = require('web.env');
    const session = require('web.session');
    const { Chrome } = require('point_of_sale.chrome');

    owl.config.mode = env.isDebug() ? 'dev' : 'prod';
    owl.Component.env = env;

    async function startPosApp(webClient) {
        await session.is_bound;
        env.qweb.addTemplates(session.owlTemplates);
        await owl.utils.whenReady();
        await webClient.setElement(document.body);
        await webClient.start();
        const chrome = new Chrome();
        chrome.mount(document.getElementsByClassName('o_action_manager')[0]);
    }

    return { startPosApp };
});
