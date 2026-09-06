/** @odoo-module **/
import { Component, signal, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

// Only match the chatter when it's rendered as a side panel (.o-aside).
// On mobile/narrow viewports Odoo drops this class and stacks the chatter
// below the form instead — in that case the toggle should stay hidden.
const CHATTER_ASIDE_SELECTOR = ".o-mail-Form-chatter.o-aside, .o-mail-ChatterContainer.o-aside";

export class ChatterToggle extends Component {
    static template = "chatter_reducer.ChatterToggleTabs";
    static props = {};

    setup() {
        this.hidden = signal(browser.localStorage.getItem("chatter_reducer.hidden") === "true");
        this.chatterAsidePresent = signal(this.checkChatterAsidePresent());
        this.applyState();

        this.observer = new MutationObserver(() => {
            this.chatterAsidePresent.set(this.checkChatterAsidePresent());
        });

        onMounted(() => {
            this.observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
        });

        onWillUnmount(() => {
            this.observer.disconnect();
        });
    }

    checkChatterAsidePresent() {
        return !!document.querySelector(CHATTER_ASIDE_SELECTOR);
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