odoo.define('point_of_sale.owlPosRoot', function (require) {
    "use strict";

    const ActionManager = require('web.ActionManager');
    const chrome = require('point_of_sale.chrome');
    const { ComponentAdapter } = require('web.OwlCompatibility');

    class PosRoot extends owl.Component {
        constructor() {
            super();
            // Pos needs to be able to print Invoices
            // this is the SOLE purpose of this actionManager
            this.actionManager = new ActionManager(this.env);
            this.actionManager.on('clear-uncommitted-changes', this, callBack => callBack());
            this.PosChrome = chrome.Chrome;
        }
        mounted() {
            odoo.isReady = true;
            this.env.bus.trigger('web-client-mounted');
            super.mounted();
        }
    };
    PosRoot.template = owl.tags.xml`
        <t t-component="ComponentAdapter" Component="PosChrome" t-att-class="'o_action_manager'"/>
    `;
    PosRoot.components = { ComponentAdapter };

    return PosRoot;
});