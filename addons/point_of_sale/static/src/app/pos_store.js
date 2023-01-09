/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { reactive, useState, toRaw } from "@odoo/owl";

export class PosStore {
    /** @type {'LOADING' | 'READY' | 'CLOSING'} */
    uiState = "LOADING";
    debugWidgetIsShown = true;
    hasBigScrollBars = false;
    notification = {
        isShown: false,
        message: "",
        duration: 2000,
    };
    loadingSkipButtonIsShown = false;
    // not using an arrow function here because we need the correct `this`
    toggleDebugWidget = debounce(function toggleDebugWidget() {
        this.debugWidgetIsShown = !toRaw(this).debugWidgetIsShown;
    }, 100);
    mainScreen = { name: null, component: null };
    tempScreen = null;
    constructor() {
        this.setup();
    }
    // to allow other modules to add things to the store.
    setup() {}
}

export const posService = {
    start() {
        return reactive(new PosStore());
    },
};

registry.category("services").add("pos", posService);

export function usePos() {
    return useState(useService("pos"));
}
