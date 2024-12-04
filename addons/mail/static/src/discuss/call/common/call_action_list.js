import { Component, useState } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "./call_actions";

export class CallActionList extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["thread", "fullscreen", "compact?"];
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.rtc = useState(useService("discuss.rtc"));
        this.callActions = useCallActions();
    }

    get MORE() {
        return _t("More");
    }

    get isOfActiveCall() {
        return Boolean(this.props.thread.eq(this.rtc.state?.channel));
    }

    get isSmall() {
        return Boolean(this.props.compact && !this.props.fullscreen.isActive);
    }

    get isMobileOS() {
        return isMobileOS();
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickRejectCall(ev) {
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        await this.rtc.leaveCall(this.props.thread);
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickToggleAudioCall(ev, { camera = false } = {}) {
        await this.rtc.toggleCall(this.props.thread, { camera });
    }
}
