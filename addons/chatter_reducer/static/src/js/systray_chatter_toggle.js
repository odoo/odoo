/** @odoo-module **/
import { Component, signal, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

const CHATTER_SELECTOR = ".o-mail-Form-chatter, .o-mail-ChatterContainer";

export class ChatterToggle extends Component {
    static template = "chatter_reducer.ChatterToggleTabs";
    static props = {};

    setup() {
        this.hidden = signal(browser.localStorage.getItem("chatter_reducer.hidden") === "true");
        this.chatterPresent = signal(this.checkChatterPresent());
        this.applyState();

        this.observer = new MutationObserver(() => {
            this.chatterPresent.set(this.checkChatterPresent());
        });

        onMounted(() => {
            this.observer.observe(document.body, { childList: true, subtree: true });
        });

        onWillUnmount(() => {
            this.observer.disconnect();
        });
    }

    checkChatterPresent() {
        return !!document.querySelector(CHATTER_SELECTOR);
    }

    applyState() {
        document.body.classList.toggle("o-chatter-reducer-hidden", this.hidden());
    }

    toggle() {
        this.hidden.set(!this.hidden());
        browser.localStorage.setItem("chatter_reducer.hidden", this.hidden());
        this.applyState();
    }
}

registry.category("main_components").add("chatter_reducer.toggle", {
    Component: ChatterToggle,
});