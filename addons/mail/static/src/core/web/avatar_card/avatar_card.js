import { ActionList } from "@mail/core/common/action_list";
import { ImStatus } from "@mail/core/common/im_status";

import { Component, computed, signal, t, useListener, useProps } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

export class AvatarCard extends Component {
    static template = "mail.AvatarCard";
    static components = { ActionList, Dropdown, DropdownItem, ImStatus };
    static get allowedModels() {
        return ["res.users", "res.partner"];
    }

    viewProfileBtnRef = signal.ref();

    setup() {
        this.props = useProps({
            close: t.function([]),
            id: t.number(),
            model: t.selection(AvatarCard.allowedModels),
        });
        this.actionService = useService("action");
        this.store = useService("mail.store");
        this.dialog = useService("dialog");
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            model: this.props.model,
        });
        this.partnerLocalDateTimeFormatted = computed(() =>
            this.store.localTimeIn(this.partner?.tz)
        );
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

/**
 * @param {import("@odoo/owl").Signal<HTMLElement>} ref
 * @param {() => import("models").ResPartner | undefined} getPartner
 */
export function usePartnerAvatarCardOnClick(ref, getPartner) {
    const avatarCard = usePopover(AvatarCard);
    useListener(ref, "click", () => {
        const partner = getPartner();
        if (!partner || avatarCard.isOpen) {
            return;
        }
        avatarCard.open(ref(), {
            id: partner.id,
            model: "res.partner",
        });
    });
}
