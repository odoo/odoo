import { CallDropdown } from "@mail/discuss/call/common/call_dropdown";

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class BlurPerformanceWarning extends Component {
    static template = "discuss.BlurPerformanceWarning";
    static props = {};
    static components = { CallDropdown };

    setup() {
        this.store = useService("mail.store");
    }

    onClickClose() {
        this.store.settings.blurPerformanceWarning = false;
    }
}
