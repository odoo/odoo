/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

import Chrome from "@point_of_sale/js/Chrome";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";
import { PosGlobalState } from "@point_of_sale/js/models";
import { configureGui } from "@point_of_sale/js/Gui";
import { registry } from "@web/core/registry";
import env from "@point_of_sale/js/pos_env";
import { debounce } from "@web/core/utils/timing";
import { batched } from "@point_of_sale/js/utils";

const { Component, reactive, markRaw, useExternalListener, useSubEnv, onWillUnmount, xml } = owl;

export class ChromeAdapter extends Component {
    setup() {
        this.PosChrome = Registries.Component.get(Chrome);
        ProductScreen.sortControlButtons();
        const legacyActionManager = useService("legacy_action_manager");

        // Instantiate PosGlobalState here to ensure that every extension
        // (or class overloads) is taken into consideration.
        const pos = PosGlobalState.create({ env: markRaw(env) });

        this.batchedCustomerDisplayRender = batched(() => {
            reactivePos.send_current_order_to_customer_facing_display();
        });
        const reactivePos = reactive(pos, this.batchedCustomerDisplayRender);
        env.pos = reactivePos;
        env.legacyActionManager = legacyActionManager;

        // The proxy requires the instance of PosGlobalState to function properly.
        env.proxy.set_pos(reactivePos);

        // TODO: Should we continue on exposing posmodel as global variable?
        // Expose only the reactive version of `pos` when in debug mode.
        window.posmodel = pos.debug ? reactivePos : pos;

        this.env = env;
        this.__owl__.childEnv = env;
        useSubEnv({
            get isMobile() {
                return window.innerWidth <= 768;
            },
        });
        let currentIsMobile = this.env.isMobile;
        const updateUI = debounce(() => {
            if (this.env.isMobile !== currentIsMobile) {
                currentIsMobile = this.env.isMobile;
                this.render(true);
            }
        }, 15);
        useExternalListener(window, "resize", updateUI);
        onWillUnmount(updateUI.cancel);
    }

    async configureAndStart(chrome) {
        // Add the pos error handler when the chrome component is available.
        registry.category("error_handlers").add(
            "posErrorHandler",
            (env, ...noEnvArgs) => {
                if (chrome) {
                    return chrome.errorHandler(this.env, ...noEnvArgs);
                }
                return false;
            },
            { sequence: 0 }
        );
        // Little trick to avoid displaying the block ui during the POS models loading
        const BlockUiFromRegistry = registry.category("main_components").get("BlockUI");
        registry.category("main_components").remove("BlockUI");
        configureGui({ component: chrome });
        await chrome.start();
        registry.category("main_components").add("BlockUI", BlockUiFromRegistry);

        // Subscribe to the changes in the models.
        this.batchedCustomerDisplayRender();
    }
}
ChromeAdapter.template = xml`<t t-component="PosChrome" setupIsDone.bind="configureAndStart"/>`;
