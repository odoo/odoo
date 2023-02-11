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

function startPosApp() {
    Registries.Component.add(owl.misc.Portal);
    Registries.Component.freeze();
    startWebClient(PosApp);
}

startPosApp();
