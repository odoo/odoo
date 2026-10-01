import { Component, types, useProps } from "@odoo/owl";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { useService } from "@web/core/utils/hooks";

export class PipBanner extends Component {
    static template = "discuss.pipBanner";
    static components = { CallActionList };

    setup() {
        super.setup();
        this.props = useProps({ compact: types.boolean().optional(false) });
        this.rtc = useService("discuss.rtc");
        useAncestors({ inDiscussCallTheme: true });
    }

    onClickClose() {
        this.rtc.closePip();
    }
}
