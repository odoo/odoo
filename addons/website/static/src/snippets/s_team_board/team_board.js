import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

export class TeamBoard extends Interaction {
    static selector = "section.s_team_board";

    dynamicContent = {
        ".s_team_board_modal": {
            "t-on-show.bs.modal": (ev) => this.updateState(ev.relatedTarget),
            "t-on-hidden.bs.modal": () => this.resetState(),
        },
        ".s_team_board_member_send_message_btn": {
            "t-on-click": this.locked(this.sendMessage, true),
        },
    };

    setup() {
        this.modalEl = this.el.querySelector(".s_team_board_modal");
        this.contactMethodsRegistry = registry.category("website.s_team_board.contact_methods");
        this.resetState();
    }

    start() {
        this.contactModal = window.Modal.getOrCreateInstance(this.modalEl);

        const contactMethodsBtnContainerEl = this.modalEl.querySelector(
            ".contact_methods_btn_container"
        );

        const buttons = this.contactMethodsRegistry
            .getEntries()
            .map((contactMethod) =>
                this.createContactMethodsButton(
                    contactMethod[1].contactType,
                    contactMethod[1].contactData
                )
            );

        contactMethodsBtnContainerEl.replaceChildren(...buttons);

        this.registerCleanup(() => {
            this.modalEl.addEventListener(
                "hidden.bs.modal",
                () => {
                    this.contactModal.dispose();
                },
                { once: true }
            );
            this.contactModal.hide();
        });
    }

    createContactMethodsButton(contactMethodType, contactMethodData) {
        const contactMethodBtn = document.createElement("button");
        const contactMethodSpan = document.createElement("span");
        contactMethodBtn.classList.add(
            "btn",
            "btn-outline-warning",
            "registered_contact_method_btn"
        );
        contactMethodSpan.classList.add("s_contact_method_cta");
        contactMethodSpan.innerText = `Copy ${contactMethodType}`;
        contactMethodBtn.appendChild(contactMethodSpan);

        this.addListener(contactMethodBtn, "click", () => {
            browser.navigator.clipboard.writeText(contactMethodData);
        });

        return contactMethodBtn;
    }

    resetState() {
        this.memberName = null;
    }

    updateState(cardEl) {
        if (!cardEl) {
            return;
        }

        this.memberName = cardEl.querySelector(".s_team_board_card_name")?.textContent.trim() || "";

        const memberRole =
            cardEl.querySelector(".s_team_board_card_designation")?.textContent.trim() || "";

        const memberDetails =
            cardEl.querySelector(".s_team_board_card_summary")?.textContent.trim() || "";

        const memberImageSrc = cardEl.querySelector(".s_team_board_member_image")?.src || "";

        this.modalEl.querySelector(".s_team_board_member_modal_name").textContent = this.memberName;
        this.modalEl.querySelector(".s_team_board_member_modal_role").textContent = memberRole;
        this.modalEl.querySelector(".s_team_board_member_modal_summary").textContent =
            memberDetails;

        this.modalEl.querySelector(".s_team_board_member_modal_img").src = memberImageSrc;
    }

    disableMsgBtn() {
        const msgBtn = this.modalEl.querySelector(".s_team_board_member_send_message_btn");
        const msgBtnSpinner = msgBtn.querySelector(".spinner-border");
        msgBtn.disabled = true;
        msgBtn.blur();
        msgBtnSpinner.classList.remove("d-none");
    }

    enableMsgBtn() {
        const msgBtn = this.modalEl.querySelector(".s_team_board_member_send_message_btn");
        const msgBtnSpinner = msgBtn.querySelector(".spinner-border");
        msgBtn.disabled = false;
        msgBtnSpinner.classList.add("d-none");
    }

    async sendMessage() {
        await this.waitFor(rpc(`/website/contact/`, { name: this.memberName })).then(
            this.protectSyncAfterAsync(() => {
                this.services.notification.add(_t("Your messsage has been sent."), {
                    type: "success",
                });
                window.Modal.getOrCreateInstance(this.modalEl).hide();
            }),
            this.protectSyncAfterAsync(() => {
                this.services.notification.add(_t("Uh oh, couldn't send your message."), {
                    type: "danger",
                });
            })
        );
    }
}

registry.category("public.interactions").add("website.s_team_board", TeamBoard);
