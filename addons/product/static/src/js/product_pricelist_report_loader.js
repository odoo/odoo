/** @odoo-module **/

import { loadLegacyAssets } from "@web/core/assets";
import { registry } from '@web/core/registry';
import { memoize } from "@web/core/utils/functions";

const actionRegistry = registry.category("actions");

const loadGeneratePriceListAction = memoize(async (env) => {
    await loadLegacyAssets();
    if (actionRegistry.get("generate_pricelist") === loadGeneratePriceListAction) {
        actionRegistry.add(
            "generate_pricelist",
            () => {
                const msg = env._t("Lazy assets backend couldn't be loaded");
                env.services.notification.add(msg, { type: "danger" });
            },
            { force: true }
        );
    }
    return {
        target: "current",
        tag: "generate_pricelist",
        type: "ir.actions.client",
    };
});

actionRegistry.add('generate_pricelist', loadGeneratePriceListAction);

// class StudioActionLoader extends Component {
//     setup() {
//         this.orm = useService("orm");
//         onWillStart(loadWysiwyg);
//         onWillStart(() => loadLegacyViews({ orm: this.orm }));
//     }
// }
// StudioActionLoader.components = { LazyComponent };
// StudioActionLoader.template = xml`
//     <LazyComponent bundle="'web.assets_backend_legacy_lazy'" Component="'StudioClientAction'" props="props"/>
// `;
// registry.category("actions").add("studio", StudioActionLoader);
