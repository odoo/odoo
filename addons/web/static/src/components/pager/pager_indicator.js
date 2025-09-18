// @ts-check

/** @module @web/components/pager/pager_indicator - Floating toast indicator showing current page position on pager updates */

import { Component, useState } from "@odoo/owl";
import { Transition } from "@web/components/transition";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";

import { PAGER_UPDATED_EVENT, pagerBus } from "./pager";

export class PagerIndicator extends Component {
    static template = "web.PagerIndicator";
    static components = { Transition };
    static props = {};

    setup() {
        this.state = useState({
            show: false,
            value: "-",
            total: 0,
        });
        this.startShowTimer = null;
        useBus(pagerBus, PAGER_UPDATED_EVENT, /** @type {any} */ (this.pagerUpdate));
    }

    pagerUpdate({ detail }) {
        this.state.value = detail.value;
        this.state.total = detail.total;
        browser.clearTimeout(this.startShowTimer);
        this.state.show = true;
        this.startShowTimer = browser.setTimeout(() => {
            this.state.show = false;
        }, 1400);
    }
}

registry.category("main_components").add("PagerIndicator", {
    Component: PagerIndicator,
});
