import { Component, useProps, types as t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FullscreenTooltip extends Component {
    static template = "discuss.FullscreenTooltip";
    static components = {};

    props = useProps({ close: t.function() });

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
    }

    onClickClose() {
        this.rtc.isFullscreenHintDismissed = true;
        this.props.close();
    }
}
