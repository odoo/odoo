import { Component, onWillStart } from "@odoo/owl";
import { isIOS, isBrowserSafari } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class InstallPWADialog extends Component {
    static props = {
        close: Function,
    };
    static template = "web.InstallPWADialog";
    static components = { Dialog };

    setup() {
        this.installPrompt = useService("installPrompt");
        this.isBrowserSafari = isBrowserSafari();
        this.isIOS = isIOS();
        onWillStart(async () => {
            this.appName = await this.installPrompt.getAppName();
        });
    }

    launchInstallProcess() {
        this.installPrompt.show({
            onDone: () => this.props.close(),
        });
    }
}
