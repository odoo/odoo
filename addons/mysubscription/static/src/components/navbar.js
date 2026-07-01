import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { _t } from "@web/core/l10n/translation";
import { navState } from "../shared_state";

// This patch allows the navbar to display "My Subscription" as the app name.
patch(NavBar.prototype, {
    get currentApp() {
        if (navState.isOpen) {
            return {
                id: "mysubscription_app",
                name: _t("My Subscription"),
                appID: "mysubscription_app",
                actionID: "mysubscription.action_mysubscription_dashboard",
            };
        }
        return super.currentApp;
    },

    get currentAppSections() {
        if (navState.isOpen) {
            return [];
        }
        return super.currentAppSections;
    }
});
