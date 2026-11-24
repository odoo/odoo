import { StorePlugin } from "@mail/core/common/store_plugin";
import { Component, types as t, usePlugin, useProps } from "@odoo/owl";

export class MicrophoneWarning extends Component {
    static template = "discuss.MicrophoneWarning";
    static components = {};

    props = useProps({ close: t.function() });

    setup() {
        super.setup();
        this.rtc = usePlugin(StorePlugin).rtc;
    }

    onClickClose() {
        if (this.rtc.showMicrophonePermissionWarning) {
            this.rtc.isMicrophonePermissionWarningDismissed = true;
        }
        this.props.close();
    }
}
