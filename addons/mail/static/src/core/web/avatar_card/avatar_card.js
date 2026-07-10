import { ActionList } from "@mail/core/common/action_list";
import { ImStatus } from "@mail/core/common/im_status";
import { useDynamicInterval } from "@mail/utils/common/misc";
import { formatLocalDateTime } from "@mail/utils/common/dates";

import { Component, props, signal, t } from "@odoo/owl";

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

    setup() {
        this.props = props({
            close: t.function([]),
            id: t.number(),
            model: t.selection(AvatarCard.allowedModels),
        });
        this.actionService = useService("action");
        this.store = useService("mail.store");
        this.dialog = useService("dialog");
        this.partnerLocalDateTimeFormatted = signal("");
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            model: this.props.model,
        });
        useDynamicInterval(() => this.onChangeTz());
    }

    onChangeTz() {
        const formatted = formatLocalDateTime(this.partner?.tz, this.store.self?.tz);
        this.partnerLocalDateTimeFormatted.set(formatted);
        if (!formatted) {
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

function getAvatarCardProps(record, model) {
    if (!record) {
        return;
    }
    if (typeof record === "number") {
        return model ? { id: record, model } : undefined;
    }
    const id = record.id ?? record.resId;
    const recordModel = record.model ?? record.resModel ?? model;
    return id && recordModel ? { id, model: recordModel } : undefined;
}

/**
 * @param {Object} param
 * @param {string | undefined} param.model
 * @param {Object | undefined} param.popoverOptions
 * @param {boolean | undefined} param.preventOpenIfOpen
 * @param {boolean | undefined} param.stopPropagation
 * @returns {{
 *   isOpen: boolean,
 *   close: () => void,
 *   open: (target: Event | HTMLElement, record: Object | number, model?: string) => boolean
 * }}
 */
export function useAvatarCard({
    model,
    popoverOptions,
    preventOpenIfOpen = true,
    stopPropagation = false,
} = {}) {
    const avatarCard = usePopover(AvatarCard, popoverOptions);
    return {
        get isOpen() {
            return avatarCard.isOpen;
        },
        close() {
            avatarCard.close();
        },
        open(target, record, recordModel = model) {
            const avatarCardProps = getAvatarCardProps(record, recordModel);
            if (!avatarCardProps || (preventOpenIfOpen && avatarCard.isOpen)) {
                return false;
            }
            if (stopPropagation) {
                target.stopPropagation?.();
            }
            avatarCard.open(target.currentTarget || target, avatarCardProps);
            return true;
        },
    };
}
