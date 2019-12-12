
odoo.define('point_of_sale.main', function (require) {
    "use strict";

    /**
     * Starts the POS.
     * It is considered as a standalone application
     * that should not need the whole infrastructure
     * of the backend
     */
    const chrome = require('point_of_sale.chrome');
    const { ComponentAdapter } = require('web.OwlCompatibility');

    const env = require('web.env');
    const session = require("web.session");

    owl.config.mode = env.isDebug() ? "dev" : "prod";
    owl.Component.env = env;

    class PosRoot extends owl.Component {
        mounted() {
            odoo.isReady = true;
            this.env.bus.trigger('web-client-mounted');
            super.mounted();
        }
    };
    PosRoot.template = owl.tags.xml`
        <t t-component="ComponentAdapter" Component="props.Component" t-att-class="'o_action_manager'"/>
    `;
    PosRoot.components = { ComponentAdapter };
    /**
     * Add the owl templates to the environment and start the web client.
     */
    async function startPOS() {
        const posRoot = new PosRoot(null, {Component: chrome.Chrome});
        await session.is_bound;
        env.qweb.addTemplates(session.owlTemplates);

        await owl.utils.whenReady();
        posRoot.mount(document.body);
    }
    startPOS();
});

odoo.define('root.widget', function (require) {
    "use strict";
    return null;
});
