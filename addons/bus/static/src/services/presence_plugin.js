import { EventBus, Plugin, signal, useListener, usePlugin } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { GlobalBusPlugin } from "@web/core/global_bus_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";

const LOCAL_STORAGE_PREFIX = "presence";

export class PresencePlugin extends Plugin {
    isOdooFocused = signal(true);
    #lastPresenceTime = signal(
        browser.localStorage.getItem(`${LOCAL_STORAGE_PREFIX}.lastPresence`) ||
            luxon.DateTime.now().ts
    );
    #globalBus = usePlugin(GlobalBusPlugin).bus;
    bus = new EventBus();

    setup() {
        useListener(browser, "storage", (ev) => this.#onStorage(ev));
        useListener(browser, "focus", () => this.#onFocusChange(true));
        useListener(browser, "blur", () => this.#onFocusChange(false));
        useListener(browser, "pagehide", () => this.#onFocusChange(false));
        useListener(browser, "click", () => this.#onPresence(), { capture: true });
        useListener(browser, "keydown", () => this.#onPresence(), { capture: true });
    }

    getLastPresence() {
        return this.#lastPresenceTime();
    }

    getInactivityPeriod() {
        return luxon.DateTime.now().ts - this.#lastPresenceTime();
    }

    #onPresence() {
        this.#lastPresenceTime.set(luxon.DateTime.now().ts);
        browser.localStorage.setItem(
            `${LOCAL_STORAGE_PREFIX}.lastPresence`,
            this.#lastPresenceTime()
        );
        this.bus.trigger("presence");
    }

    #onFocusChange(isFocused) {
        try {
            isFocused = parent.document.hasFocus();
        } catch {
            // noop
        }
        this.isOdooFocused.set(isFocused);
        browser.localStorage.setItem(`${LOCAL_STORAGE_PREFIX}.focus`, this.isOdooFocused());
        if (this.isOdooFocused()) {
            this.#lastPresenceTime.set(luxon.DateTime.now().ts);
            this.#globalBus.trigger("window_focus", this.isOdooFocused());
        }
    }

    #onStorage({ key, newValue }) {
        if (key === `${LOCAL_STORAGE_PREFIX}.focus`) {
            this.isOdooFocused.set(JSON.parse(newValue));
            this.#globalBus.trigger("window_focus", newValue);
        }
        if (key === `${LOCAL_STORAGE_PREFIX}.lastPresence`) {
            this.#lastPresenceTime.set(JSON.parse(newValue));
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
export const presenceService = {
    start() {
        const presencePlugin = usePlugin(PresencePlugin);
        const presenceService = Object.create(presencePlugin);
        presenceService.getLastPresence = presencePlugin.getLastPresence.bind(presencePlugin);
        presenceService.getInactivityPeriod =
            presencePlugin.getInactivityPeriod.bind(presencePlugin);
        return presenceService;
    },
};

registry.category("services").add("presence", presenceService);
