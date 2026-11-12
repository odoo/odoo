import { propStatic, usePropsPlus } from "@mail/utils/common/hooks";
import { Component, types as t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FullscreenHint extends Component {
    static template = "discuss.FullscreenHint";

    setup() {
        super.setup();
        this.props = usePropsPlus({ close: propStatic(t.function()) });
        this.rtc = useService("discuss.rtc");
    }

    onClickClose() {
        this.rtc.isFullscreenHintDismissed = true;
        this.props.close();
    }
}
