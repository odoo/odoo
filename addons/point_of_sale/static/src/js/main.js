odoo.define('point_of_sale.main', function (require) {
    "use strict";

    /**
     * Starts the POS.
     * It is considered as a standalone application
     * that should not need the whole infrastructure
     * of the backend
     */
    const env = require('web.env');
    const PosRoot = require('point_of_sale.owlPosRoot');
    const session = require("web.session");

    owl.config.mode = env.isDebug() ? "dev" : "prod";
    owl.Component.env = env;

    /**
     * Add the owl templates to the environment and start the web client.
     */
    async function startPOS() {
        const posRoot = new PosRoot(null);
        await session.is_bound;
        env.qweb.addTemplates(session.owlTemplates);

        await owl.utils.whenReady();
        posRoot.mount(document.body);
    }
    startPOS();
});
