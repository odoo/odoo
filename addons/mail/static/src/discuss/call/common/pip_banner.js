import { useSubEnv } from "@web/owl2/utils";
import { Component, props, types } from "@odoo/owl";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { useService } from "@web/core/utils/hooks";

export class PipBanner extends Component {
    static template = "discuss.pipBanner";
    static components = { CallActionList };

    setup() {
        super.setup();
        this.props = props({ compact: types.boolean().optional(false) });
        this.rtc = useService("discuss.rtc");
        useSubEnv({ isDiscussPipBanner: true });
    }

    onClickClose() {
        this.rtc.closePip();
    }
}
