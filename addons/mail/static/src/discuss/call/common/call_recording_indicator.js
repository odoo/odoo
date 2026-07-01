import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";

export class CallRecordingIndicator extends Component {
    static template = "discuss.CallRecordingIndicator";
    static props = [];

    setup() {
        this.rtc = useService("discuss.rtc");
        // FIXME does not work when the call controls are in overlay mode
        // should maybe be part of the call controls?
        // FIXME flicker due to button size when hovering
        // TODO layout for chat window
        this.rootHover = useHover("root");
    }

    onClickStopRecording() {
        this.rtc.stopRecordingDebounce();
    }
}
