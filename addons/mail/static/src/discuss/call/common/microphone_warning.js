import { Component, useProps, types as t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MicrophoneWarning extends Component {
    static template = "discuss.MicrophoneWarning";
    static components = {};

    props = useProps({ close: t.function() });

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
    }

    onClickClose() {
        if (this.rtc.showMicrophonePermissionWarning) {
            this.rtc.isMicrophonePermissionWarningDismissed = true;
        }
        if (this.rtc.showTalkWhileMutedSuggestion) {
            this.rtc.isTalkWhileMutedSuggestionDismissed = true;
            this.rtc.showTalkWhileMutedSuggestion = false;
        }
        this.props.close();
    }

    onClickDisableTalkWhileMutedSuggestion() {
        this.rtc.isTalkWhileMutedSuggestionDisabled = true;
        this.rtc.showTalkWhileMutedSuggestion = false;
        this.props.close();
    }
}
