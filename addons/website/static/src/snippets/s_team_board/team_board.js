import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { usePlugin, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";
import { _t } from "@web/core/l10n/translation";
export const contactActionsRegistry = registry.category("website.team_board_snippet.modal_actions");

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";

    dynamicContent = {
        ".o_team_board_modal": {
            "t-on-show.bs.modal": (ev) => {
                const cardEl = ev.relatedTarget?.closest(".o_team_board_card");
                if (cardEl) {
                    this.updateModal(cardEl);
                }
            },
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
        this.modalFooter = this.modalEl.querySelector(".modal-footer");

        onWillDestroy(() => {
            this.modalInstance.hide();
        });
    }

    start() {
        this.renderActionButtons();
    }

    // setting up actions button from registery
    get contactActions() {
        return contactActionsRegistry
            .getAll()
            .sort((a, b) => (a.sequence || 100) - (b.sequence || 100));
    }

    renderActionButtons() {
        if (!this.modalFooter) {
            return;
        }

        this.modalFooter.innerHTML = "";
        for (const actionItem of this.contactActions) {
            const btn = this.createBtn(actionItem);
            this.modalFooter.appendChild(btn);
        }
    }

    createBtn(actionItem) {
        const btn = document.createElement("button");
        btn.className = `btn ${actionItem.btnClass || "btn-primary"}`;
        btn.textContent = actionItem.label;

        this.addListener(
            btn,
            "click",
            this.locked(async () => {
                const originalText = btn.textContent;
                if (actionItem.loadingLabel) {
                    btn.textContent = actionItem.loadingLabel;
                }
                try {
                    const result = await this.waitFor(
                        actionItem.action({
                            notification: this.notification,
                            modalInstance: this.modalInstance,
                        })
                    );
                    this.protectSyncAfterAsync((shouldHide) => {
                        if (shouldHide) {
                            this.modalInstance.hide();
                        }
                    })(result);
                } catch (error) {
                    this.protectSyncAfterAsync((err) => {
                        console.error(_t("Modal action failed :"), err);
                    })(error);
                } finally {
                    this.protectSyncAfterAsync(() => {
                        btn.textContent = originalText;
                    })();
                }
            }, true)
        );
        return btn;
    }

    // handle card click
    updateModal(card) {
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
}

registry.category("public.interactions").add("website.team_board", TeamBoard);

// send message action
contactActionsRegistry.add("send_message", {
    id: "send_message",
    label: "Send Message",
    loadingLabel: "Sending...",
    btnClass: "btn-primary",
    sequence: 10,
    action: async ({ notification }) => {
        const shouldFail = Math.random() < 0.5;
        try {
            await new Promise((resolve, reject) => {
                setTimeout(
                    () => (shouldFail ? reject(new Error("Random error")) : resolve()),
                    1000
                );
            });
            notification.add(_t("Message sent!"), {
                title: "Success",
                type: "success",
            });
        } catch {
            notification.add(_t("Could not send your message"), {
                title: "Error",
                type: "danger",
                sticky: true,
            });
            return false;
        }
        return true;
    },
});
