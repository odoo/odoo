/** @odoo-module */

import { startWebClient } from "@web/start";

import { ChromeAdapter } from "@point_of_sale/js/chrome_adapter";
import Registries from "point_of_sale.Registries";
import { registry } from "@web/core/registry";

// For consistency's sake, we should trigger"WEB_CLIENT_READY" on the bus when PosApp is mounted
// But we can't since mail and some other poll react on that cue, and we don't want those services started
class PosApp extends owl.Component {
    setup() {
        this.Components = registry.category("main_components").getEntries();
    }
}
PosApp.template = owl.tags.xml`
  <body>
    <ChromeAdapter />
    <div>
      <t t-foreach="Components" t-as="C" t-key="C[0]">
        <t t-component="C[1].Component" t-props="C[1].props"/>
      </t>
    </div>
  </body>
`;
PosApp.components = { ChromeAdapter };

<<<<<<< HEAD
function startPosApp() {
    Registries.Component.add(owl.misc.Portal);
    Registries.Component.freeze();
    startWebClient(PosApp);
}
=======
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
        configureGui({ component: chrome });
        await chrome.start();
    }
>>>>>>> 900e3ca057d... temp

startPosApp();
