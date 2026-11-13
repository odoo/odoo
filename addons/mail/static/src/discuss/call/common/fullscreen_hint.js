import { Component, useProps, types as t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FullscreenHint extends Component {
    static template = "discuss.FullscreenHint";

    setup() {
        super.setup();
        this.props = useProps({ close: t.function().static() });
        this.rtc = useService("discuss.rtc");
    }

    onClickClose() {
        this.rtc.isFullscreenHintDismissed = true;
        this.props.close();
    }
}
