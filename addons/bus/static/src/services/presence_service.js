import { computed, config, EventBus, plugin, Plugin, signal, useListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";

const LOCAL_STORAGE_PREFIX = "presence";

export class PresencePlugin extends Plugin {
    isOdooFocused = signal(true);
    lastPresenceTime = signal(
        browser.localStorage.getItem(`${LOCAL_STORAGE_PREFIX}.lastPresence`) ||
        luxon.DateTime.now().ts
    );
    inactivityPeriod = computed(() => {
        return luxon.DateTime.now().ts - this.lastPresenceTime();
    });
    env = config("env");
    bus = new EventBus();

    setup() {
        useListener(browser, "storage", () => this.onStorage());
        useListener(browser, "focus", () => this.onFocusChange(true));
        useListener(browser, "blur", () => this.onFocusChange(false));
        useListener(browser, "pagehide", () => this.onFocusChange(false));
        useListener(browser, "click", () => this.onPresence(), { capture: true });
        useListener(browser, "keydown", () => this.onPresence(), { capture: true });
    }

    /**
     * @private
     */
    onPresence() {
        this.lastPresenceTime.set(luxon.DateTime.now().ts);
        browser.localStorage.setItem(`${LOCAL_STORAGE_PREFIX}.lastPresence`, this.lastPresenceTime());
        this.bus.trigger("presence");
    }

    /**
     * @private
     */
    onFocusChange(isFocused) {
        try {
            isFocused = parent.document.hasFocus();
        } catch {
            // noop
        }
        this.isOdooFocused.set(isFocused);
        browser.localStorage.setItem(`${LOCAL_STORAGE_PREFIX}.focus`, this.isOdooFocused());
        if (this.isOdooFocused()) {
            this.lastPresenceTime.set(luxon.DateTime.now().ts);
            this.env.bus.trigger("window_focus", this.isOdooFocused());
        }
    }

    /**
     * @private
     */
    onStorage({ key, newValue }) {
        if (key === `${LOCAL_STORAGE_PREFIX}.focus`) {
            this.isOdooFocused.set(JSON.parse(newValue));
            this.env.bus.trigger("window_focus", newValue);
        }
        if (key === `${LOCAL_STORAGE_PREFIX}.lastPresence`) {
            this.lastPresenceTime.set(JSON.parse(newValue));
            this.bus.trigger("presence");
        }
    }
}

services.add(PresencePlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the presence service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("presence", {
    start() {
        const presencePlugin = plugin(PresencePlugin);
        const presenceService = Object.create(presencePlugin);
        presenceService.getLastPresence = function() {
            return presencePlugin.lastPresenceTime();
        }
        presenceService.isOdooFocused = function() {
            return presencePlugin.isOdooFocused();
        }
        presenceService.getInactivityPeriod = function() {
            return presencePlugin.inactivityPeriod();
        }
        return presenceService;
    }
});
