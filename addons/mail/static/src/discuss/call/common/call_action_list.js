import { Component, useRef } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { CallActionButton } from "@mail/discuss/call/common/call_action_button";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { CALL_PROMOTE_FULLSCREEN } from "@mail/discuss/call/common/thread_model_patch";

export class CallActionList extends Component {
    static components = { Dropdown, DropdownItem, CallActionButton };
    static props = ["thread", "fullscreen", "compact?"];
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.CALL_PROMOTE_FULLSCREEN = CALL_PROMOTE_FULLSCREEN;
        this.store = useService("mail.store");
        this.callActions = useCallActions();
        this.more = useRef("more");
        this.popover = usePopover(Tooltip, {
            position: "top-middle",
        });
    }

    get rtc() {
        return this.store.rtc;
    }

    get MORE() {
        return _t("More");
    }

    get isOfActiveCall() {
        return Boolean(this.props.thread.eq(this.rtc.channel));
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
        await this.rtc.toggleCall(this.props.thread, { camera, fullscreen: this.props.fullscreen });
    }

    onMouseenterMore() {
        if (this.props.thread.promoteFullscreen === CALL_PROMOTE_FULLSCREEN.ACTIVE) {
            this.popover.open(this.more.el, { tooltip: _t("Enter full screen!") });
            this.props.thread.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.DISCARDED;
        }
    }

    onMouseleaveMore() {
        if (this.popover.isOpen) {
            this.popover.close();
        }
    }

    onClickMore() {
        if (this.popover.isOpen) {
            this.popover.close();
        }
    }
}
