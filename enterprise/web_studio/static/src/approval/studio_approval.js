/** @odoo-module */

import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { StudioApprovalInfos } from "@web_studio/approval/approval_infos";
import { Component, onWillUnmount, useRef } from "@odoo/owl";

function useOpenExternal() {
    const closeFns = [];
    function open(_open) {
        const close = _open();
        closeFns.push(close);
        return close;
    }

    onWillUnmount(() => {
        closeFns.forEach((cb) => cb());
    });
    return open;
}

export class StudioApproval extends Component {
    static props = {
        approval: Object,
    };
    static template = "StudioApproval";

    setup() {
        this.dialog = useService("dialog");
        this.popover = usePopover(StudioApprovalInfos);
        this.rootRef = useRef("root");
        this.openExternal = useOpenExternal();
    }

    get approval() {
        return this.props.approval;
    }

    get state() {
        return this.approval.state;
    }

    toggleApprovalInfo() {
        if (this.env.isSmall) {
            if (this.isOpened) {
                this.closeInfos();
                this.closeInfos = null;
                return;
            }
            const onClose = () => {
                this.isOpened = false;
            };
            this.closeInfos = this.openExternal(() =>
                this.dialog.add(
                    StudioApprovalInfos,
                    { approval: this.approval, isPopover: false },
                    { onClose }
                )
            );
        } else {
            this.popover.open(this.rootRef.el, { approval: this.approval, isPopover: true });
        }
    }

    getEntry(ruleId) {
        return this.state.entries.find((e) => e.rule_id[0] === ruleId);
    }
}
