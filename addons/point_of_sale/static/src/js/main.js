odoo.define('web.web_client', function (require) {
    'use strict';

    const env = require('web.env');
    const WebClient = require('web.AbstractWebClient');
    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const { configureGui } = require('point_of_sale.Gui');

    owl.config.mode = env.isDebug() ? 'dev' : 'prod';
    owl.Component.env = env;

    async function startPosApp(webClient) {
        Registries.Component.freeze();
        await env.session.is_bound;
        env.qweb.addTemplates(env.session.owlTemplates);
        await owl.utils.whenReady();
        await webClient.setElement(document.body);
        await webClient.start();
        const chrome = new (Registries.Component.get(Chrome))(null, { webClient });
        await chrome.mount(document.querySelector('.o_action_manager'));
        await chrome.start();
        configureGui({ component: chrome });
    }

    const webClient = new WebClient();
    startPosApp(webClient);
    return webClient;
});
