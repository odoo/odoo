import { Component, proxy, signal, t, useListener, useProps, markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Interaction } from "@web/public/interaction";
import { browser } from "@web/core/browser/browser";

export class SendMessageModal extends Component {
    static template = "website.SendMessageModal";
    static components = { Dialog };

    props = useProps({
        close: t.function(),
        cardHtml: t.string(),
        name: t.string(),
    });

    setup() {
        this.state = proxy({ sending: false });
        this.notification = useService("notification");

 
        this.modalRef = signal.ref();
        useListener(this.modalRef, "click", (ev) => this.onClickOutside(ev));
    }

    get cardContent() {
        return markup(this.props.cardHtml);

    }

    onClickOutside(ev) {
        if (ev.target === ev.currentTarget && !this.state.sending) {
            this.props.close();
        }
    }

    async sendMessage() {
        if (this.state.sending) {
            return;
        }
        this.state.sending = true;

        try {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            this.props.close();
            this.notification.add(_t("Your message has been sent."), { type: "success" });
        } catch {
            this.state.sending = false;
            this.notification.add(_t("Your message could not be sent."), { type: "danger" });
        }
    }

    async copyEmail() {
        const email = `${this.props.name.toLowerCase().replaceAll(" ", ".")}@test.test`;
        try {
            await browser.navigator.clipboard.writeText(email);
            this.notification.add(_t("Email copied."), { type: "success" });
        } catch {
            this.notification.add(_t("Could not copy the email."), { type: "danger" });
        }
    }
}

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";

    dynamicContent = {
        ".s_team_board_card": {
            "t-on-click": this.onClickCard,
            "t-on-keydown": this.onKeydownCard,
            "t-att-role": () => "button",
            "t-att-tabindex": () => "0",
            "t-att-aria-haspopup": () => "dialog",
        },
    };

    setup() {
        this.closeModal = null;
    }

    destroy() {
        this.closeModal?.();
    }

    onClickCard(ev) {
        this.openCardModal(ev.currentTarget);
    }

    onKeydownCard(ev) {
        if (ev.key !== "Enter" && ev.key !== " ") {
            return;
        }
        ev.preventDefault();
        this.openCardModal(ev.currentTarget);
    }

    openCardModal(card) {
        const data = {
            cardHtml: card.innerHTML,
            name: card.querySelector(".o_card_title")?.textContent.trim() || "",

        };
        this.closeModal = this.services.dialog.add(SendMessageModal, data, {
            onClose: () => {
                this.closeModal = null;
            },
        });
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
