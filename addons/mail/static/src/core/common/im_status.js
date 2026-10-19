import { Component, t } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";
import { attClassObjectToString } from "@mail/utils/common/format";
import { propComputed } from "@mail/utils/common/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/** @typedef {import("registries").ImStatusData} ImStatusData */

export const imStatusDataRegistry = registry.category("mail.im_status_data");

/**
 * @param {Object} param0
 * @param {import("models").ChannelMember} [param0.member]
 * @param {import("models").MailGuest|import("models").ResPartner} param0.persona
 * @param {import("models").ResUsers} [param0.user]
 * @returns {ImStatusData}
 */
export function getImStatusData({ member, persona, user }) {
    const data = imStatusDataRegistry.getAll().find((r) => r.condition({ member, persona, user }));
    return /** @type {ImStatusData} */ (
        Object.fromEntries(
            ["icon", "iconClass", "title"].map((key) => {
                const value = data[key];
                return [
                    key,
                    typeof value === "string" || value instanceof String
                        ? value
                        : value[persona.imStatusUI] ?? value.default,
                ];
            })
        )
    );
}

imStatusDataRegistry.add(
    "mail",
    {
        condition: () => true,
        icon: {
            online: "circle",
            away: "contrast",
            busy: "remove_circle",
            offline: "circle",
            default: "help",
        },
        iconClass: {
            online: "oi-filled",
            away: "",
            busy: "",
            offline: "",
            default: "",
        },
        title: {
            online: _t("User is online"),
            away: _t("User is idle"),
            busy: _t("User is busy"),
            offline: _t("User is offline"),
            default: _t("No IM status available"),
        },
    },
    { sequence: 100 }
);

imStatusDataRegistry.add(
    "bot",
    {
        condition: ({ persona }) => persona?.isBot,
        icon: "favorite",
        iconClass: "oi-filled o-imStatus-bot",
        title: _t("User is a bot"),
    },
    { sequence: 90 }
);

export class ImStatus extends Component {
    static template = "mail.ImStatus";
    static components = { Typing };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.className = propComputed("className", t.string().optional(""));
        this.member = propComputed(
            "member",
            t.instanceOf(this.store["discuss.channel.member"]).optional()
        );
        this.personaProp = propComputed(
            "persona",
            t
                .or([
                    t.instanceOf(this.store["res.partner"]),
                    t.instanceOf(this.store["mail.guest"]),
                ])
                .optional()
        );
        this.size = propComputed("size", t.string().optional("lg"));
        this.style = propComputed("style", t.string().optional(""));
        this.typing = propComputed("typing", t.boolean().optional(true));
        this.userProp = propComputed("user", t.instanceOf(this.store["res.users"]).optional());
        this.attClassObjectToString = attClassObjectToString;
    }

    get persona() {
        return this.userProp()?.partner_id || this.personaProp() || this.member()?.persona;
    }

    get showTypingIndicator() {
        return this.typing() && this.member()?.isTypingUi;
    }

    get class() {
        return attClassObjectToString({
            [`o-mail-ImStatus d-flex ${this.colorClass} ${this.className()}`]: true,
            [`rounded-circle bg-transparent ${this.iconClass}`]: !this.showTypingIndicator,
            "rounded-pill": this.showTypingIndicator,
        });
    }

    get activeImStatusData() {
        return getImStatusData({
            member: this.member(),
            persona: this.persona,
            user: this.user,
        });
    }

    get icon() {
        return this.activeImStatusData.icon;
    }

    get iconClass() {
        return this.activeImStatusData.iconClass;
    }

    get title() {
        return this.activeImStatusData.title;
    }

    get colorClass() {
        switch (this.persona.imStatusUI) {
            case "bot":
            case "online":
                return "text-success";
            case "away":
                return "o-yellow";
            case "busy":
                return "text-danger";
            case "offline":
                return "text-700 opacity-75";
            default:
                return "opacity-75";
        }
    }

    get user() {
        return this.userProp() || this.persona?.main_user_id;
    }
}
