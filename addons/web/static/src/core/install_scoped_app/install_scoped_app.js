import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Component, onMounted, useState } from "@odoo/owl";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class InstallScopedApp extends Component {
    static props = {};
    static template = "web.InstallScopedApp";
    static components = { Dropdown };
    setup() {
        this.pwa = useState(useService("pwa"));
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
    onChangeName(ev) {
        const value = ev.target.value;
        if (value !== this.state.manifest.name) {
            const url = new URL(document.location.href);
            url.searchParams.set("app_name", encodeURIComponent(value));
            browser.location.replace(url);
        }
    }
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

registry.category("public_components").add("web.install_scoped_app", InstallScopedApp);
