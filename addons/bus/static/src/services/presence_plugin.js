import { EventBus, Plugin, signal, useListener, usePlugin } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { useChildEnv } from "@web/owl2/utils";

const LOCAL_STORAGE_PREFIX = "presence";

export class PresencePlugin extends Plugin {
    isOdooFocused = signal(true);
    /** @private */
    lastPresenceTime = signal(
        browser.localStorage.getItem(`${LOCAL_STORAGE_PREFIX}.lastPresence`) ||
            luxon.DateTime.now().ts
    );
    /** @private */
    env = useChildEnv();
    bus = new EventBus();

    setup() {
        useListener(browser, "storage", this.onStorage.bind(this));
        useListener(browser, "focus", () => this.onFocusChange(true));
        useListener(browser, "blur", () => this.onFocusChange(false));
        useListener(browser, "pagehide", () => this.onFocusChange(false));
        useListener(browser, "click", this.onPresence.bind(this), { capture: true });
        useListener(browser, "keydown", this.onPresence.bind(this), { capture: true });
    }

    getInactivityPeriod() {
        return luxon.DateTime.now().ts - this.lastPresenceTime();
    }

    /** @private */
    onPresence() {
        this.lastPresenceTime.set(luxon.DateTime.now().ts);
        browser.localStorage.setItem(
            `${LOCAL_STORAGE_PREFIX}.lastPresence`,
            this.lastPresenceTime()
        );
        this.bus.trigger("presence");
    }

    /** @private */
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
        const presencePlugin = usePlugin(PresencePlugin);
        const presenceService = Object.create(presencePlugin);
        presenceService.getLastPresence = function () {
            return presencePlugin.lastPresenceTime();
        };
        return presenceService;
    },
});
