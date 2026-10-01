import { _t } from "@web/core/l10n/translation";
import { Interaction } from "@web/public/interaction";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { usePlugin } from "@odoo/owl";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";
    dynamicContent = {
        ".s_team_board_member": {
            "t-att-data-bs-toggle": () => "modal",
            "t-att-data-bs-target": () => ".o_team_board_modal",
            "t-att-role": () => "button",
        },
        ".o_team_board_modal": {
            "t-on-show.bs.modal": (ev) => this.updateModal(ev.relatedTarget),
        },
        ".o_team_board_member_send_message_btn": {
            "t-on-click": this.locked(this.sendMessage, true),
        },
    };

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
        this.modalEl = this.el.querySelector(".o_team_board_modal");
        this.sendBtnEl = this.modalEl?.querySelector(".o_team_board_member_send_message_btn");
    }

    updateModal(memberEl) {
        const imgEl = memberEl.querySelector(".s_team_board_member_img ");
        const contentEl = memberEl.querySelector(".s_team_board_member_content");

        const modalImgEl = this.modalEl.querySelector(".o_team_board_modal_img");
        const modalContentEl = this.modalEl.querySelector(".o_team_board_modal_content");

        modalImgEl.src = imgEl?.src || "/web/static/img/placeholder.png";
        modalImgEl.alt = imgEl?.alt || "";

        modalContentEl.replaceChildren(...contentEl.cloneNode(true).childNodes);

        this.currentMemberName = memberEl.querySelector(".card-title")?.textContent.trim() || "";
    }

    async sendMessage() {
        const sendBtnLabel = this.sendBtnEl.textContent;
        this.sendBtnEl.textContent = _t("Sending...");
        try {
            const result = await this.waitFor(
                rpc("/website/contact", { member_name: this.currentMemberName })
            );
            if (!result.success) {
                throw new Error(result.error);
            }
            this.bootstrap.getOrCreateInstance(window.Modal, this.modalEl).hide();
            this.services.notification.add(_t("Your message has been sent."), {
                type: "success",
            });
        } catch {
            this.services.notification.add(_t("Your message could not be sent."), {
                type: "danger",
            });
        } finally {
            this.sendBtnEl.textContent = sendBtnLabel;
        }
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
