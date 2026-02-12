import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";
import { attClassObjectToString } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const imStatusDataRegistry = registry.category("mail.im_status_data");

imStatusDataRegistry.add(
    "bot",
    {
        condition: ({ persona, store }) => persona.eq(store.odoobot),
        icon: "fa fa-heart o-xsmaller o-pt-0_5",
        color: "text-success",
        title: _t("User is a bot"),
    },
    { sequence: 90 }
);

imStatusDataRegistry.add(
    "mail",
    {
        condition: () => true,
        icon: {
            online: "fa fa-circle",
            away: "fa fa-adjust",
            busy: "fa fa-minus-circle",
            offline: "fa fa-circle-o",
            default: "fa fa-question-circle",
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

export class ImStatus extends Component {
    static props = ["persona?", "className?", "style?", "member?", "slots?", "size?", "typing?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "", size: "lg", typing: true };
    static components = { Typing };

    setup() {
        super.setup();
        this.attClassObjectToString = attClassObjectToString;
        this.store = useService("mail.store");
    }

    get persona() {
        return this.props.persona ?? this.props.member?.persona;
    }

    get showTypingIndicator() {
        return this.props.typing && this.props.member?.isTyping;
    }

    get class() {
        return attClassObjectToString({
            [`o-mail-ImStatus d-flex ${this.icon} ${this.colorClass} ${this.props.className}`]: true,
            "o-fs-small": this.persona?.im_status !== "bot",
            "rounded-circle bg-transparent": !this.showTypingIndicator,
            "rounded-pill": this.showTypingIndicator,
        });
    }

    get activeImStatusData() {
        return imStatusDataRegistry
            .getAll()
            .find((r) =>
                r.condition({ store: this.store, persona: this.persona, member: this.props.member })
            );
    }

    get icon() {
        const data = this.activeImStatusData;
        return data.icon[this.persona.im_status] || data.icon.default || data.icon;
    }

    get title() {
        const data = this.activeImStatusData;
        return data.title[this.persona.im_status] || data.title.default || data.title;
    }

    get colorClass() {
        const data = this.activeImStatusData;
        if (data.color) {
            return data.color;
        }
        switch (this.persona.im_status) {
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
}
