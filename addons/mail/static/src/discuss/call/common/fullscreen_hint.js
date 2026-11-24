import { StorePlugin } from "@mail/core/common/store_plugin";
import { Component, types as t, usePlugin, useProps } from "@odoo/owl";

export class FullscreenHint extends Component {
    static template = "discuss.FullscreenHint";

    setup() {
        super.setup();
        this.close = useProps.static("close", t.function());
        this.rtc = usePlugin(StorePlugin).rtc;
    }

    onClickClose() {
        this.rtc.isFullscreenHintDismissed = true;
        this.close();
    }
}
