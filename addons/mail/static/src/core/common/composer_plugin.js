import { subscribeToStorage } from "@mail/utils/common/local_storage";

import { onWillDestroy, Plugin, signal } from "@odoo/owl";

import { services } from "@web/core/services";

/**
 * Enable Html composer with:
 * odoo.__WOWL_DEBUG__.root.__owl__.pluginManager.getPluginById("ComposerPlugin").setHtmlComposer()
 */
export class ComposerPlugin extends Plugin {
    #htmlEnabled = signal(JSON.parse(window.localStorage.getItem("mail.html_composer.enabled")));

    setup() {
        onWillDestroy(
            subscribeToStorage("mail.html_composer.enabled", ({ newValue }) =>
                this.#htmlEnabled.set(JSON.parse(newValue))
            )
        );
    }

    get htmlEnabled() {
        return this.#htmlEnabled();
    }

    setHtmlComposer() {
        if (this.#htmlEnabled()) {
            return;
        }
        this.#htmlEnabled.set(true);
        window.localStorage.setItem("mail.html_composer.enabled", true);
    }

    setTextComposer() {
        if (!this.#htmlEnabled()) {
            return;
        }
        this.#htmlEnabled.set(false);
        window.localStorage.setItem("mail.html_composer.enabled", false);
    }
}

services.add(ComposerPlugin);
