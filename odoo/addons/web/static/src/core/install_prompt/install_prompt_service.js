/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import {
    isDisplayStandalone,
    isIOS,
    isMacOS,
    isBrowserSafari,
} from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { InstallPrompt } from "./install_prompt";

const serviceRegistry = registry.category("services");

const installPromptService = {
    dependencies: ["dialog"],
    start(env, { dialog }) {
        let nativePrompt;

        const state = reactive({
            canPromptToInstall: false,
            decline,
            show,
        });

        // The PWA can only be installed if the app is not already launched (display-mode standalone)
        // For Apple devices, PWA are supported on any mobile version of Safari, or in desktop since version 17
        // On Safari devices, the check is also done on the display-mode and we rely on the installationState to
        // decide whether we must show the prompt or not
        const canBeInstalled =
            browser.BeforeInstallPromptEvent !== undefined ||
            (isBrowserSafari() &&
                !isDisplayStandalone() &&
                (isIOS() ||
                    (isMacOS() && browser.navigator.userAgent.match(/Version\/(\d+)/)[1] >= 17)));

        const installationState = browser.localStorage.getItem("pwa.installationState");
        const isDeclined = installationState === "dismissed";

        if (canBeInstalled && !isDeclined) {
            browser.addEventListener("beforeinstallprompt", (ev) => {
                // This event is only triggered by the browser when the native prompt to install can be shown
                // This excludes incognito tabs, as well as visiting the website while the app is installed
                nativePrompt = ev;
                if (installationState === "accepted") {
                    // If this event is triggered with the installationState stored, it means that the app has been
                    // removed since its installation. The prompt can be displayed, and the installation state is reset.
                    browser.localStorage.removeItem("pwa.installationState");
                }
                state.canPromptToInstall = true;
            });
            if (isBrowserSafari()) {
                // since those platforms don't rely on the beforeinstallprompt event, we handle it ourselves
                state.canPromptToInstall = installationState !== "accepted";
            }
        }

        async function show() {
            if (!state.canPromptToInstall) {
                return;
            }
            if (nativePrompt) {
                const res = await nativePrompt.prompt();
                browser.localStorage.setItem("pwa.installationState", res.outcome);
                state.canPromptToInstall = false;
            } else if (isBrowserSafari()) {
                // since those platforms don't support a native installation prompt yet, we
                // show a custom dialog to explain how to pin the app to the application menu
                dialog.add(InstallPrompt, {
                    onClose: () => this.decline(),
                });
            }
        }

        function decline() {
            browser.localStorage.setItem("pwa.installationState", "dismissed");
            state.canPromptToInstall = false;
        }

        return state;
    },
};
serviceRegistry.add("installPrompt", installPromptService);
