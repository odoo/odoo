odoo.define('web.web_client', function (require) {
    'use strict';

    const AbstractService = require('web.AbstractService');
    const env = require('web.env');
    const WebClient = require('web.AbstractWebClient');
    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const { configureGui } = require('point_of_sale.Gui');

    owl.config.mode = env.isDebug() ? 'dev' : 'prod';
    owl.Component.env = env;

    Registries.Component.add(owl.misc.Portal);

    function setupResponsivePlugin(env) {
        const isMobile = () => window.innerWidth <= 768;
        env.isMobile = isMobile();
        const updateEnv = owl.utils.debounce(() => {
            if (env.isMobile !== isMobile()) {
                env.isMobile = !env.isMobile;
                env.qweb.forceUpdate();
            }
        }, 15);
        window.addEventListener("resize", updateEnv);
    }

    setupResponsivePlugin(owl.Component.env);

    async function startPosApp(webClient) {
        Registries.Component.freeze();
        await env.session.is_bound;
        env.qweb.addTemplates(env.session.owlTemplates);
        env.bus = new owl.core.EventBus();
        await owl.utils.whenReady();
        await webClient.setElement(document.body);
        await webClient.start();
        webClient.isStarted = true;
        const chrome = new (Registries.Component.get(Chrome))(null, { webClient });
        await chrome.mount(document.querySelector('.o_action_manager'));
        await chrome.start();
        configureGui({ component: chrome });
    }

    AbstractService.prototype.deployServices(env);
    const webClient = new WebClient();
    startPosApp(webClient);
    return webClient;
});
