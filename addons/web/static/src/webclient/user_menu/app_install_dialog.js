/** @odoo-module */

import { Component } from "@odoo/owl";
import { isAndroid, isBrowserChrome, isIOS } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class AppInstallDialog extends Component {
    static template = "web.AppInstallDialog";
    static components = { Dialog };

    setup() {
        this.isChrome = isBrowserChrome();
        this.isIOS = isIOS();
        this.isAndroid = isAndroid();

        this.installPrompt = useService("installPrompt");

        console.log("AppInstallDialog setup");
    }

    launchInstallProcess() {
        console.log(this.installPrompt.canPromptToInstall);
        this.installPrompt.show();
    }
}
