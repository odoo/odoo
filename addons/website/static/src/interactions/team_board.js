import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { SendMessageModal } from "./team_board_modal";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";

    dynamicContent = {
        ".s_team_board_card .o_team_board_card_btn": {
            "t-on-click": this.onCardClick,
        },
    };

    setup() {
        this.closeModal = null;
    }

    destroy() {
        this.closeModal?.();
    }

    onCardClick(ev) {
        this.openCardModal(ev.currentTarget.closest(".s_team_board_card"));
    }

    openCardModal(cardEl) {
        const data = {
            imageSrc: cardEl.querySelector("img")?.getAttribute("src") || "",
            name: cardEl.querySelector(".card-title")?.textContent.trim() || "",
            jobPosition: cardEl.querySelector(".o_job_position")?.textContent.trim() || "",
            infos: cardEl.querySelector(".o_card_infos")?.textContent.trim() || "",
        };
        this.closeModal = this.services.dialog.add(SendMessageModal, data, {
            onClose: () => {
                this.closeModal = null;
            },
        });
        this.registerCleanup(this.closeModal);
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
