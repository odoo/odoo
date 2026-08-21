import { Component, useProps, types as t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FullscreenTooltip extends Component {
    static template = "discuss.FullscreenTooltip";

    setup() {
        super.setup();
        this.close = useProps.static("close", t.function());
        console.log("close:", typeof this.close, this.close);
        this.rtc = useService("discuss.rtc");
    }

    onClickClose() {
        this.rtc.isFullscreenHintDismissed = true;
        this.close();
    }
}
