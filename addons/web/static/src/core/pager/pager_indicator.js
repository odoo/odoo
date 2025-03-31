import { browser } from "../browser/browser";
import { registry } from "../registry";
import { Transition } from "../transition";
import { useBus } from "../utils/hooks";

import { Component, useState } from "@odoo/owl";
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
        useBus(pagerBus, PAGER_UPDATED_EVENT, this.pagerUpdate);
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
