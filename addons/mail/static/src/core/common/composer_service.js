import { subscribeToStorage } from "@mail/utils/common/local_storage";

import { signal } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const composerService = {
    dependencies: ["mail.store"],
    /**
     * Enable Html composer with: odoo.__WOWL_DEBUG__.root.env.services["mail.composer"].setHtmlComposer()
     */
    start(env, services) {
        const store = services["mail.store"];
        const htmlEnabled = signal(
            JSON.parse(browser.localStorage.getItem("mail.html_composer.enabled"))
        );
        store.onChange(
            () => [],
            () =>
                subscribeToStorage("mail.html_composer.enabled", ({ newValue }) =>
                    htmlEnabled.set(JSON.parse(newValue))
                )
        );
        return {
            get htmlEnabled() {
                return htmlEnabled();
            },
            setHtmlComposer() {
                if (htmlEnabled()) {
                    return;
                }
                htmlEnabled.set(true);
                browser.localStorage.setItem("mail.html_composer.enabled", true);
            },
            setTextComposer() {
                if (!htmlEnabled()) {
                    return;
                }
                htmlEnabled.set(false);
                browser.localStorage.setItem("mail.html_composer.enabled", false);
            },
        };
    },
};

registry.category("services").add("mail.composer", composerService);
