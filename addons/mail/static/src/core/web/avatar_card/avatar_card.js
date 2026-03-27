import { useState } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";
import { ImStatus } from "@mail/core/common/im_status";
import { useDynamicInterval } from "@mail/utils/common/misc";
import { formatLocalDateTime } from "@mail/utils/common/dates";
import { ActionList } from "@mail/core/common/action_list";

export class AvatarCard extends Component {
    static template = "mail.AvatarCard";
    static components = { ActionList, Dropdown, DropdownItem, ImStatus };
    static props = {
        id: { type: Number },
        close: { type: Function },
        model: {
            type: String,
            validate: (m) => AvatarCard.allowedModels.includes(m),
        },
    };
    static get allowedModels() {
        return ["res.users", "res.partner"];
    }

    setup() {
        this.actionService = useService("action");
        this.store = useService("mail.store");
        this.dialog = useService("dialog");
        this.state = useState({ partnerLocalDateTimeFormatted: "" });
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            model: this.props.model,
        });
        useDynamicInterval(
            (...args) => this.onChangeTz(...args),
            () => [this.partner?.tz, this.store.self?.tz]
        );
    }

    /**
     * @param {string} partnerTz
     * @param {string} currentUserTz
     */
    onChangeTz(partnerTz, currentUserTz) {
        this.state.partnerLocalDateTimeFormatted = formatLocalDateTime(partnerTz, currentUserTz);
        if (!this.state.partnerLocalDateTimeFormatted) {
            return;
        }
        return 60000 - (Date.now() % 60000);
    }

    get avatarUrl() {
        if (this.partner) {
            return this.partner.avatarUrl;
        }
        if (this.user) {
            return this.user.avatarUrl;
        }
        return `/web/image/${this.props.model}/${this.props.id}/avatar_128`;
    }

    get displayAvatar() {
        return Boolean(this.partner || this.user);
    }

    get user() {
        if (this.props.model === "res.users") {
            return this.store["res.users"].get(this.props.id);
        }
        if (this.props.model === "res.partner") {
            return this.store["res.partner"].get(this.props.id)?.main_user_id;
        }
        return undefined;
    }

    get partner() {
        if (this.props.model === "res.partner") {
            return this.store["res.partner"].get(this.props.id);
        }
        return this.user?.partner_id;
    }

    get name() {
        return this.partner?.name;
    }

    get email() {
        return this.partner?.email;
    }

    get phone() {
        return this.partner?.phone;
    }

    get showViewProfileBtn() {
        return Boolean(this.partner);
    }

    get hasFooter() {
        return false;
    }

    async getProfileAction() {
        return {
            res_id: this.partner.id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    onSendClick() {
        if (this.user) {
            this.store.openChat({ userId: this.user.id });
        }
        this.props.close();
    }

    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        this.props.close();
        if (!action) {
            return;
        }
        this.actionService.doAction(action, { newWindow });
    }
}
