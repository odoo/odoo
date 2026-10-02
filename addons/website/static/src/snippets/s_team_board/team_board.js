import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { usePlugin, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";

    dynamicContent = {
        ".o_team_board_card": {
            "t-att-data-bs-toggle": () => "modal",
            "t-att-data-bs-target": () => ".o_team_board_modal",
            "t-att-role": () => "button",
        },
        ".o_team_board_modal": {
            "t-on-show.bs.modal": (ev) => this._updateModal(ev.relatedTarget),
        },
        ".s_team_board_send_btn": {
            "t-on-click": this.locked(this.onSendMessage, true),
        },
    };

    setup() {
        this.notification = useService("notification");
        this.bootstrap = usePlugin(BootstrapInstance);

        this.modalEl = this.el.querySelector(".modal");
        this.modalInstance = this.bootstrap.getOrCreateInstance(window.Modal, this.modalEl, {
            keyboard: true,
            backdrop: true,
        });

        this.modalImg = this.modalEl.querySelector(".modal-body img");
        this.modalName = this.modalEl.querySelector(".modal-header h3");
        this.modalRole = this.modalEl.querySelector(".modal-body h6");
        this.modalDesc = this.modalEl.querySelector(".modal-body p");
        this.modalButton = this.modalEl.querySelector(".s_team_board_send_btn");

        onWillDestroy(() => {
            this.modalInstance.hide();
        });
    }

    destroy() {
        this.modalInstance.hide();
    }

    // handle card click
    _updateModal(card) {
        const data = {
            name: card.querySelector(".card-title")?.textContent.trim(),
            function: card.querySelector(".card-subtitle.text-secondary")?.textContent.trim(),
            description: card.querySelector(".card-text:not(.text-secondary)")?.textContent.trim(),
            picture: card.querySelector("img.o_card_img")?.getAttribute("src"),
        };

        this.modalImg.setAttribute("src", data.picture);
        this.modalName.textContent = data.name;
        this.modalRole.textContent = data.function;
        this.modalDesc.textContent = data.description;
    }

    _onClickCard(ev) {
        const card = ev.target.closest(".o_team_board_card");
        if (!card) {
            return;
        }
        this._updateModal(card);
        this.modalInstance.show();
    }

    // handle modal action button
    async onSendMessage() {
        const btnLabel = this.modalButton.textContent;
        this.modalButton.textContent = "Processing ...";

        try {
            await this.fakeApiCall();
            this.notification.add("Your message has been sent", {
                title: "Success",
                type: "success",
                sticky: false,
            });
            this.modalInstance.hide();
        } catch {
            this.notification.add("Could not send your message", {
                title: "Error",
                type: "danger",
                sticky: true,
            });
        }

        this.modalButton.textContent = btnLabel;
    }

    async fakeApiCall(failureProbability = 0.5) {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                const shouldFail = Math.random() < failureProbability;

                if (shouldFail) {
                    reject(new Error("Random error"));
                } else {
                    resolve();
                }
            }, 2000);
        });
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
