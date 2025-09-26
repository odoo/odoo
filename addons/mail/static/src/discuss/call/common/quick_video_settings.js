import { Component } from "@odoo/owl";

import { CallSettingsDialog } from "@mail/discuss/call/common/call_settings";
import { DeviceSelect } from "@mail/discuss/call/common/device_select";

import { useService } from "@web/core/utils/hooks";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

export class QuickVideoSettings extends Component {
    static template = "discuss.QuickVideoSettings";
    static props = [];
    static components = { DeviceSelect };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.dialogService = useService("dialog");
        this.isBrowserSafari = isBrowserSafari;
    }

    onClickVideoSettings() {
        this.dialogService.add(CallSettingsDialog, {});
    }
}
