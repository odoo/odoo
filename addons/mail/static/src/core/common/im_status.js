import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";
import { attClassObjectToString } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const imStatusDataRegistry = registry.category("mail.im_status_data");

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
        icon_class: {
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
        icon_class: "oi-filled o-xsmaller o-pt-0_5",
        title: _t("User is a bot"),
    },
    { sequence: 90 }
);

export class ImStatus extends Component {
    static props = [
        "className?",
        "member?",
        "persona?",
        "size?",
        "slots?",
        "style?",
        "typing?",
        "user?",
    ];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "", size: "lg", typing: true };
    static components = { Typing };

    setup() {
        super.setup();
        this.attClassObjectToString = attClassObjectToString;
    }

    get persona() {
        return this.props.user?.partner_id || this.props.persona || this.props.member?.persona;
    }

    get showTypingIndicator() {
        return this.props.typing && this.props.member?.isTypingUi;
    }

    get class() {
        return attClassObjectToString({
            [`o-mail-ImStatus d-flex ${this.colorClass} ${this.props.className}`]: true,
            "o-fs-small": !this.persona?.isBot,
            [`rounded-circle bg-transparent ${this.iconClass}`]: !this.showTypingIndicator,
            "rounded-pill": this.showTypingIndicator,
        });
    }

    get activeImStatusData() {
        return imStatusDataRegistry
            .getAll()
            .find((r) =>
                r.condition({ member: this.props.member, persona: this.persona, user: this.user })
            );
    }

    get icon() {
        const data = this.activeImStatusData;
        return data.icon[this.persona.imStatusUI] || data.icon.default || data.icon;
    }

    get iconClass() {
        const data = this.activeImStatusData;
        return data.icon_class[this.persona.imStatusUI] || data.icon_class.default || data.icon_class;
    }

    get title() {
        const data = this.activeImStatusData;
        return data.title[this.persona.imStatusUI] || data.title.default || data.title;
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
        return this.props.user || this.persona?.main_user_id;
    }
}
