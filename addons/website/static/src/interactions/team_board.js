import { _t } from "@web/core/l10n/translation";
import { Interaction } from "@web/public/interaction";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class TeamBoard extends Interaction {
    static selector = "section.s_team_board";
    dynamicContent = {
        ".s_team_board_member": {
            "t-att-data-bs-toggle": () => "modal",
            "t-att-data-bs-target": () => ".o_team_board_modal",
            "t-att-role": () => "button",
        },
    };

    setup() {
        this.modal = this.el.querySelector(".o_team_board_modal");
    }

    start() {
        if (!this.modal) {
            return;
        }
        const placeholder = document.createComment("o_team_board_modal");
        this.modal.before(placeholder);
        document.body.appendChild(this.modal);

        this.modalInst = window.Modal.getOrCreateInstance(this.modal);
        this.sendBtn = this.modal.querySelector(".o_team_board_member_send_message_btn");

        this.addListener(this.modal, "show.bs.modal", (ev) =>
            this.updateModal(ev.relatedTarget)
        );

        this.addListener(this.sendBtn, "click", this.locked(this.sendMessage, true));

        this.registerCleanup(() => {
            this.modalInst.dispose();
            placeholder.replaceWith(this.modal);
        });
    }

    updateModal(member) {
        const member_fields = { name: ".card-title", role: ".text-muted", bio: ".card-text" };

        const img = member.querySelector("img");
        const modalImg = this.modal.querySelector(".o_team_board_modal_img");
        modalImg.src = img.src;
        modalImg.alt = img.alt;
        for (const [field, selector] of Object.entries(member_fields)) {
            this.modal.querySelector(`.o_team_board_modal_${field}`).textContent =
                member.querySelector(selector).textContent;
        }
    }

    async sendMessage() {
        const sendBtnLabel = this.sendBtn.textContent;
        this.sendBtn.textContent = _t("Sending...");
        try {
            const result = await this.waitFor(
                rpc("/website/contact", { member_name: this.currentMemberName })
            );
            if (!result.success) {
                throw new Error(result.error);
            }
            this.modalInst.hide();
            this.services.notification.add(_t("Your message has been sent."), {
                type: "success",
            });
        } catch {
            this.services.notification.add(_t("Your message could not be sent."), {
                type: "danger",
            });
        } finally {
        this.sendBtn.textContent = sendBtnLabel;
        }
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
