import { Component, props, types as t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MicrophoneWarning extends Component {
    static template = "discuss.MicrophoneWarning";
    static components = {};

    props = props({ close: t.function() });

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
    }

    onClickClose() {
        if (this.rtc.showMicrophonePermissionWarning) {
            this.rtc.isMicrophonePermissionWarningDismissed = true;
        }
        this.props.close();
    }
}
