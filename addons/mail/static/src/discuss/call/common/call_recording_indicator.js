import { Component, signal, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHover } from "@mail/utils/common/hooks";

export class CallRecordingIndicator extends Component {
    static template = "discuss.CallRecordingIndicator";

    props = useProps({ className: t.string().optional("") });
    rootRef = signal.ref();

    setup() {
        this.rtc = useService("discuss.rtc");
        this.rootHover = useHover(this.rootRef);
    }
}
