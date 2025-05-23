import { Component } from "@odoo/owl";
import { CallActionList } from "@mail/discuss/call/common/call_action_list";
import { useService } from "@web/core/utils/hooks";

export class PipBanner extends Component {
    static template = "discuss.pipBanner";
    static props = {};
    static components = { CallActionList };

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
    }

    onClickClose() {
        this.rtc.closePip();
    }
}
