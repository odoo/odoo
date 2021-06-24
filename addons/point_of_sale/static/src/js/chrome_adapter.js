/** @odoo-module */

import { useService } from "@web/core/service_hook";

import Chrome from "point_of_sale.Chrome";
import Registries from "point_of_sale.Registries";
import { configureGui } from "point_of_sale.Gui";
import { useBus } from "@web/core/bus_hook";
import PosComponent from "point_of_sale.PosComponent";
import PopupControllerMixin from "point_of_sale.PopupControllerMixin";
import { registry } from "@web/core/registry";

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

export class ChromeAdapter extends PopupControllerMixin(PosComponent) {
    setup() {
        this.PosChrome = Registries.Component.get(Chrome);
        this.legacyActionManager = useService("legacy_action_manager");

        this.env = owl.Component.env;
        useBus(this.env.qweb, "update", () => this.render());
        const chrome = owl.hooks.useRef("chrome");
        owl.hooks.onMounted(async () => {
            // Little trick to avoid displaying the block ui during the POS models loading
            const BlockUiFromRegistry = registry.category("main_components").get("BlockUI");
            registry.category("main_components").remove("BlockUI");
            await chrome.comp.start();
            registry.category("main_components").add("BlockUI", BlockUiFromRegistry);
            configureGui({ component: chrome.comp });
            setupResponsivePlugin(this.env);
        });
    }
}
ChromeAdapter.template = owl.tags.xml`<PosChrome t-ref="chrome" webClient="legacyActionManager"/>`;
