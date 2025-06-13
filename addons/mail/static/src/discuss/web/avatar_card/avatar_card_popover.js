import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { showRealtimeTzDiff } from "@mail/utils/common/dates";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.users");
        this.state = useState({
            showUserTime: false,
            userTime: null,
            userDate: null,
            otherUserTz: null
        });
        let stopRealtimeTzDiff = () => {};
        onWillStart(async () => {
            const recordModel = this.props.recordModel || "res.users";
            [this.user] = await this.orm.read(recordModel, [this.props.id], this.fieldNames);
            const targetUserTz = this.user.tz || null;
            const currentPartner = Object.values(session.storeData?.["res.partner"] || {}).find(p => p.active);
            const currentUserTz = currentPartner?.tz || null;
            if (targetUserTz && currentUserTz && targetUserTz !== currentUserTz) {
                stopRealtimeTzDiff = showRealtimeTzDiff(currentUserTz, targetUserTz, ({ otherUserTime, otherUserDate }) => {
                    Object.assign(this.state, {
                        showUserTime: true,
                        userTime: otherUserTime,
                        userDate: otherUserDate,
                        otherUserTz: targetUserTz,
                    });
                });
            }
        });
        onWillUnmount(() => {
            stopRealtimeTzDiff();
        });
    }

    get fieldNames() {
        return ["name", "email", "phone", "im_status", "share", "partner_id", "tz"];
    }

    get email() {
        return this.user.email;
    }

    get phone() {
        return this.user.phone;
    }

    get showViewProfileBtn() {
        return true;
    }

    get hasFooter() {
        return false;
    }

    async getProfileAction() {
        return {
            res_id: this.user.partner_id[0],
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    get userId() {
        return this.user.id;
    }

    onSendClick() {
        this.openChat(this.userId);
        this.props.close();
    }

    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        this.actionService.doAction(action, { newWindow });
    }
}
