import { Component } from "@odoo/owl";

import { CallSettingsDialog } from "@mail/discuss/call/common/call_settings";
import { DeviceSelect } from "@mail/discuss/call/common/device_select";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class QuickVoiceSettings extends Component {
    static template = "discuss.QuickVoiceSettings";
    static components = { DeviceSelect };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.dialogService = useService("dialog");
        this.isMobile = isMobileOS;
    }

    onClickVoiceSettings() {
        this.dialogService.add(CallSettingsDialog, {});
    }

    get pttKeyDisplayText() {
        return _t("Press [%(shortcut)s]", { shortcut: this.store.settings.pushToTalkKeyText });
    }
}
