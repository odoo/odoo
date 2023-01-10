/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import { pos_env as legacyEnv } from "@point_of_sale/js/pos_env";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { reactive, useState, markRaw } from "@odoo/owl";

export class PosStore {
    /** @type {'LOADING' | 'READY' | 'CLOSING'} */
    uiState = "LOADING";
    hasBigScrollBars = false;
    loadingSkipButtonIsShown = false;
    mainScreen = { name: null, component: null };
    tempScreen = null;
    legacyEnv = legacyEnv;
    constructor() {
        this.setup();
    }
    // use setup instead of constructor because setup can be patched.
    setup() {
        this.globalState = new PosGlobalState({ env: markRaw(legacyEnv) });
    }
}

export const posService = {
    start() {
        return reactive(new PosStore());
    },
};

registry.category("services").add("pos", posService);

/**
 * @returns {PosStore}
 */
export function usePos() {
    return useState(useService("pos"));
}
