/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import { pos_env as legacyEnv } from "@point_of_sale/js/pos_env";

import { registry } from "@web/core/registry";
import { reactive, markRaw } from "@odoo/owl";
import { Reactive } from "@point_of_sale/utils";

export class PosStore extends Reactive {
    /** @type {'LOADING' | 'READY' | 'CLOSING'} */
    uiState = "LOADING";
    hasBigScrollBars = false;
    loadingSkipButtonIsShown = false;
    mainScreen = { name: null, component: null };
    tempScreen = null;
    legacyEnv = legacyEnv;
    globalState = new PosGlobalState({ env: markRaw(legacyEnv) });

    static serviceDependencies = ["popup"];
    constructor({ popup }) {
        super();
        this.popup = popup;
        this.setup();
    }
    // use setup instead of constructor because setup can be patched.
    setup() {}

    showScreen(name, props) {
        const component = registry.category("pos_screens").get(name);
        this.mainScreen = { component, props };
        // Save the screen to the order so that it is shown again when the order is selected.
        if (component.storeOnOrder ?? true) {
            this.globalState.get_order()?.set_screen_data({ name, props });
        }
    }

    closeScreen() {
        const { name: screenName } = this.globalState.get_order().get_screen_data();
        this.showScreen(screenName);
    }

    // FIXME POSREF get rid of temp screens entirely?
    showTempScreen(name, props = {}) {
        return new Promise((resolve) => {
            this.tempScreen = {
                name,
                component: registry.category("pos_screens").get(name),
                props: { ...props, resolve },
            };
        });
    }

    closeTempScreen() {
        this.tempScreen = null;
    }
}

export const posService = {
    dependencies: PosStore.serviceDependencies,
    start(env, deps) {
        return reactive(new PosStore(deps));
    },
};

registry.category("services").add("pos", posService);
