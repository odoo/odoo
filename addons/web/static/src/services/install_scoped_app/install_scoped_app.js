// @ts-check

/** @module @web/services/install_scoped_app/install_scoped_app - Public page component for installing scoped Progressive Web Apps */

import { Component, onMounted, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { browser } from "@web/core/browser/browser";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
/**
 * Public page component that lets users install a scoped Progressive Web App.
 * Displays the app manifest info, allows renaming, and triggers the PWA install prompt.
 */
export class InstallScopedApp extends Component {
    static props = {};
    static template = "web.InstallScopedApp";
    static components = { Dropdown };
    setup() {
        this.pwa = useService(/** @type {any} */ ("pwa"));
        this.state = useState({ manifest: {}, showInstallUI: false });
        this.isDisplayStandalone = isDisplayStandalone();
        // BeforeInstallPrompt event can take while before the browser triggers it. Some will display
        // immediately, others will wait that the user has interacted for some time with the website.
        this.isInstallationPossible = browser.BeforeInstallPromptEvent !== undefined;
        onMounted(async () => {
            this.state.manifest = await this.pwa.getManifest();
            this.state.showInstallUI = true;
        });
    }
    /**
     * Reload the page with a new `app_name` query parameter when the user
     * modifies the app name input.
     * @param {Event} ev
     */
    onChangeName(ev) {
        const value = /** @type {any} */ (ev.target).value;
        if (value !== this.state.manifest.name) {
            const url = new URL(document.location.href);
            url.searchParams.set("app_name", encodeURIComponent(value));
            browser.location.replace(url);
        }
    }
    /** Trigger the PWA install prompt and redirect to the app on acceptance. */
    onInstall() {
        this.state.showInstallUI = false;
        this.pwa.show({
            onDone: (res) => {
                if (res.outcome === "accepted") {
                    browser.location.replace(this.state.manifest.start_url);
                } else {
                    this.state.showInstallUI = true;
                }
            },
        });
    }
}

registry
    .category("public_components")
    .add("web.install_scoped_app", /** @type {any} */ (InstallScopedApp));
