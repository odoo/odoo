import { StorePlugin } from "@mail/core/common/store_plugin";
import { Component, signal, t, usePlugin, useProps } from "@odoo/owl";
import { useHover } from "@mail/utils/common/hooks";

export class CallRecordingIndicator extends Component {
    static template = "discuss.CallRecordingIndicator";

    props = useProps({ className: t.string().optional("") });
    rootRef = signal.ref();

    setup() {
        this.rtc = usePlugin(StorePlugin).rtc;
        this.rootHover = useHover(this.rootRef);
    }
}
