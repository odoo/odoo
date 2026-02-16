import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// TODO fix flicker
export class CallRecordingIndicator extends Component {
    static template = "discuss.CallRecordingIndicator";
    static props = [];

    setup() {
        this.rtc = useService("discuss.rtc");
        this.state = useState({ hovered: false });
    }

    onClickStopRecording() {
        this.rtc.stopRecordingDebounce();
    }
}
