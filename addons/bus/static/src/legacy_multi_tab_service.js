import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { EventBus } from "@odoo/owl";

export const legacyMultiTabService = {
    start() {
        const bus = new EventBus();

        // PROPERTIES
        const sanitizedOrigin = location.origin.replace(/:\/{0,2}/g, "_");
        const localStoragePrefix = `${this.name}.${sanitizedOrigin}.`;

        function generateLocalStorageKey(baseKey) {
            return localStoragePrefix + baseKey;
        }

        function getItemFromStorage(key, defaultValue) {
            const item = browser.localStorage.getItem(generateLocalStorageKey(key));
            try {
                return item ? JSON.parse(item) : defaultValue;
            } catch {
                return item;
            }
        }

        function setItemInStorage(key, value) {
            browser.localStorage.setItem(generateLocalStorageKey(key), JSON.stringify(value));
        }

        function onStorage({ key, newValue }) {
            if (key && key.includes(localStoragePrefix)) {
                // Only trigger the shared_value_updated event if the key is
                // related to this service/origin.
                const baseKey = key.replace(localStoragePrefix, "");
                bus.trigger("shared_value_updated", { key: baseKey, newValue });
            }
        }

        browser.addEventListener("storage", onStorage);

        return {
            bus,
            generateLocalStorageKey,
            getItemFromStorage,
            setItemInStorage,
            /**
             * Get value shared between all the tabs.
             *
             * @param {string} key
             * @param {any} defaultValue Value to be returned if this
             * key does not exist.
             */
            getSharedValue(key, defaultValue) {
                return getItemFromStorage(key, defaultValue);
            },
            /**
             * Set value shared between all the tabs.
             *
             * @param {string} key
             * @param {any} value
             */
            setSharedValue(key, value) {
                if (value === undefined) {
                    return this.removeSharedValue(key);
                }
                setItemInStorage(key, value);
            },
            /**
             * Remove value shared between all the tabs.
             *
             * @param {string} key
             */
            removeSharedValue(key) {
                browser.localStorage.removeItem(generateLocalStorageKey(key));
            },
        };
    },
};

registry.category("services").add("legacy_multi_tab", legacyMultiTabService);
