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
    };

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
        this.modalEl = this.el.querySelector(".o_team_board_modal");
        this.contactMethods = registry.category("website.s_team_board.button_methods");
    }

    start() {
        if (!this.modalEl) {
            return;
        }
        for (const method of this.contactMethods.getAll()) {
            const btn = this.createButton(method.label, method.className ?? "");
            this.addListener(btn, "click", this.locked(() => this.runButtonMethod(method, btn), true));
        }
    }

    updateModal(memberEl) {
        const imgEl = memberEl.querySelector(".s_team_board_member_img");
        const contentEl = memberEl.querySelector(".s_team_board_member_content");

        const modalImgEl = this.modalEl.querySelector(".o_team_board_modal_img");
        const modalContentEl = this.modalEl.querySelector(".o_team_board_modal_content");

        modalImgEl.src = imgEl?.src || "/web/static/img/placeholder.png";
        modalImgEl.alt = imgEl?.alt || "";

        modalContentEl.replaceChildren(...contentEl.cloneNode(true).childNodes);

        this.currentMemberName = memberEl.querySelector(".card-title")?.textContent.trim() || "";
    }

    createButton(label, className) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `btn btn-primary ${className}`;
        btn.textContent = label;
        this.modalEl.querySelector(".o_team_board_modal_buttons").append(btn);
        this.registerCleanup(() => btn.remove());

        return btn;
    }

    async runButtonMethod(method, btn) {
        const label = btn.textContent;
        btn.textContent = method.loadingLabel ?? label;
        try {
            await this.waitFor(
                method.onClick({
                    memberName: this.currentMemberName,
                })
            );
            this.protectSyncAfterAsync(() => {
                if (method.closeOnSuccess !== false) {
                    this.bootstrap.getOrCreateInstance(window.Modal, this.modalEl).hide();
                }
                this.services.notification.add(method.successMessage, { type: "success" });
            })();
        } catch {
            this.protectSyncAfterAsync(() => {
                this.services.notification.add(method.errorMessage, { type: "danger" });
            })();
        } finally {
            this.protectSyncAfterAsync(() => {
                btn.textContent = label;
            })();
        }
    }
}

registry.category("website.s_team_board.button_methods").add(
    "send_message",
    {
        label: _t("Send a message"),
        loadingLabel: _t("Sending..."),
        successMessage: _t("Your message has been sent."),
        errorMessage: _t("Your message could not be sent."),
        async onClick({ memberName }) {
            const result = await rpc("/website/contact", { member_name: memberName });
            if (!result.success) {
                throw new Error(result.error);
            }
        },
    },
    { sequence: 10 }
);

registry.category("public.interactions").add("website.team_board", TeamBoard);
