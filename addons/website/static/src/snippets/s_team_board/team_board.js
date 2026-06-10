import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";

    dynamicContent = {
        ".s_team_board_modal": {
            "t-on-show.bs.modal": this.updateState,
        },
        ".s_team_board_modal_button": {
            "t-on-click": this.locked(this.sendMessage, true),
        },
    };

    setup() {
        this.modal = this.el.querySelector(".s_team_board_modal");
        document.querySelectorAll(".modal").forEach((modal) => {
            modal.addEventListener("hide.bs.modal", () => {
                document.activeElement.blur();
            });
        });
    }

    destroy() {
        const modalEl = window.Modal.getOrCreateInstance(this.modal);
        this.el.addEventListener("hidden.bs.modal", () => modalEl.dispose(), {
            once: true,
            passive: true,
        });
        modalEl.hide();
    }

    updateState(ev) {
        const cardEl = ev.relatedTarget;
        const name = cardEl.querySelector(".s_team_board_name")?.textContent.trim() || "";
        const position = cardEl.querySelector(".s_team_board_position")?.textContent.trim() || "";
        const summary = cardEl.querySelector(".s_team_board_summary")?.textContent.trim() || "";
        const pictureSrc = cardEl.querySelector(".s_team_board_picture")?.src || "";

        this.modal.querySelector(".s_team_board_modal_name").textContent = name;
        this.modal.querySelector(".s_team_board_modal_position").textContent = position;
        this.modal.querySelector(".s_team_board_modal_summary").textContent = summary;
        this.modal.querySelector(".s_team_board_modal_picture").src = pictureSrc;
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
}

registry.category("public.interactions").add("website.s_team_board", TeamBoard);
