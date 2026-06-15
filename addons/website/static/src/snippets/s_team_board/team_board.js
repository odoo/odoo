import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { browser } from "@web/core/browser/browser";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";

    dynamicContent = {
        ".s_team_board_modal": {
            "t-on-show.bs.modal": this.onTeamBoardCardClick,
        },
        ".s_team_board_modal_button": {
            "t-on-click": this.locked(this.sendMessage, true),
        },
        ".s_team_board_contact_button": {
            "t-on-click": this.copyContactToClipboard,
        },
        ".s_team_board_member_card": {
            "t-att-data-bs-toggle": () => "modal",
            "t-att-data-bs-target": () => "#s_team_board_modal",
        },
        ".s_team_board_modal_picture": {
            "t-att-src": () => this.currentTeamCard.imgSrc,
        },
        ".s_team_board_modal_body": {
            "t-out": () => this.currentTeamCard.bodyContent,
        },
    };

    setup() {
        this.modal = this.el.querySelector(".s_team_board_modal");
        this.contactRegistry = registry.category("website.team_board.contact_methods");
        this.currentTeamCard = { imgSrc: "", bodyContent: "" };
    }

    start() {
        const contactButtons = this.contactRegistry
            .getEntries()
            .map(([contactMethodType, contactMethodData]) =>
                this.createContactMethodButton(contactMethodType, contactMethodData)
            );
        document
            .querySelector(".s_team_board_modal_contact_buttons")
            .replaceChildren(...contactButtons);
    }

    destroy() {
        const modalEl = window.Modal.getOrCreateInstance(this.modal);
        this.el.addEventListener("hidden.bs.modal", () => modalEl.dispose(), {
            once: true,
            passive: true,
        });
        modalEl.hide();
    }

    onTeamBoardCardClick(ev) {
        const cardEl = ev.relatedTarget;
        this.currentTeamCard.imgSrc = cardEl.querySelector(".o_team_board_picture")?.src || "";
        this.currentTeamCard.bodyContent =
            markup(cardEl.querySelector(".card-body")?.innerHTML) || "";
    }

    async sendMessage(ev) {
        const msgSent = await rpc("/website/team_board_contact");
        this.protectSyncAfterAsync(() => {
            if (msgSent.success) {
                this.services.notification.add(msgSent.statusMsg, {
                    type: "success",
                });
                window.Modal.getOrCreateInstance(this.modal).hide();
            } else {
                this.services.notification.add(msgSent.statusMsg, {
                    type: "danger",
                });
            }
        })();
    }

    createContactMethodButton(contactMethodType, contactMethodData) {
        const contactBtnEl = document.createElement("button");

        contactBtnEl.classList.add("btn", "btn-secondary", "m-1", "s_team_board_contact_button");
        contactBtnEl.dataset.contactMethod = contactMethodType;
        contactBtnEl.dataset.contactMethodData = contactMethodData;
        contactBtnEl.innerText = `Copy ${contactMethodType}`;

        return contactBtnEl;
    }

    copyContactToClipboard(ev) {
        const contactMethod = ev.target.dataset.contactMethod;
        const contactMethodData = ev.target.dataset.contactMethodData;
        browser.navigator.clipboard.writeText(contactMethodData);
        this.services.notification.add(`${contactMethod} has been copied to your clipboard.`, {
            type: "success",
        });
    }
}

registry.category("public.interactions").add("website.s_team_board", TeamBoard);
