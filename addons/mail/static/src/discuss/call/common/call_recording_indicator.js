import { Component, signal } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";

export class CallRecordingIndicator extends Component {
    static template = "discuss.CallRecordingIndicator";
    static props = [];

    rootRef = signal.ref();

    setup() {
        this.rtc = useService("discuss.rtc");
        // TODO layout for chat window
        this.rootHover = useHover(this.rootRef);
    }

    onClickStopRecording() {
        this.rtc.stopRecordingDebounce();
    }
}
