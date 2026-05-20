import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

let nextModalId = 0;

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";
    dynamicContent = {
        ".s_card": {
            "t-on-click": this.onCardClick,
            "t-on-keydown": this.onCardKeydown,
        },
        ".s_team_board_modal_send": {
            "t-on-click": this.onSendClick,
        },
        ".s_team_board_modal_close": {
            "t-on-click": this.onCloseClick,
        },
        ".s_team_board_modal": {
            "t-on-hidden.bs.modal": this.onModalHidden,
        },
    };

    setup() {
        this.modalEl = this.el.querySelector(".s_team_board_modal");
        const uid = `s_team_board_modal_title_${++nextModalId}`;
        const titleEl = this.modalEl.querySelector(".modal-title");
        titleEl.id = uid;
        this.modalEl.setAttribute("aria-labelledby", uid);

        this.titleEl = titleEl;
        this.roleEl = this.modalEl.querySelector(".s_team_board_modal_role");
        this.bioEl = this.modalEl.querySelector(".s_team_board_modal_bio");
        this.imgEl = this.modalEl.querySelector(".s_team_board_modal_img");
        this.sendBtnEl = this.modalEl.querySelector(".s_team_board_modal_send");
        this.defaultSendLabel = this.sendBtnEl.dataset.defaultLabel || this.sendBtnEl.textContent;

        this.bsModal = window.Modal.getOrCreateInstance(this.modalEl);
        this.registerCleanup(() => this.bsModal.dispose());

        this.currentMember = null;
    }

    extractMember(cardEl) {
        const titleEl = cardEl.querySelector(".card-title");
        const roleEl = cardEl.querySelector(".card-body .text-muted");
        const bodyParas = cardEl.querySelectorAll(".card-body p");
        const lastP = bodyParas[bodyParas.length - 1];
        const bioEl = lastP && lastP !== roleEl ? lastP : null;
        const imgEl = cardEl.querySelector(".o_card_img");
        return {
            name: (titleEl?.textContent || "").trim(),
            role: (roleEl?.textContent || "").trim(),
            bio: (bioEl?.textContent || "").trim(),
            imgSrc: imgEl?.getAttribute("src") || "",
            imgAlt: imgEl?.getAttribute("alt") || "",
        };
    }

    openModalForCard(cardEl) {
        if (!this.modalEl) {
            return;
        }
        const member = this.extractMember(cardEl);
        // Placeholder demo: every third card fails the simulated send so
        // both the success and failure UIs can be exercised without a
        // backend round-trip.
        const cards = Array.from(this.el.querySelectorAll(".s_card"));
        this.shouldFailSend = cards.indexOf(cardEl) % 3 === 2;
        this.currentMember = member;
        this.titleEl.textContent = member.name;
        this.roleEl.textContent = member.role;
        this.bioEl.textContent = member.bio;
        this.imgEl.setAttribute("src", member.imgSrc);
        this.imgEl.setAttribute("alt", member.imgAlt || member.name);
        this.resetSendButton();
        this.bsModal.show();
    }

    onCardClick(ev) {
        this.openModalForCard(ev.currentTarget);
    }

    onCardKeydown(ev) {
        if (ev.key !== "Enter" && ev.key !== " " && ev.key !== "Spacebar") {
            return;
        }
        ev.preventDefault(); // Space would otherwise scroll the page.
        this.openModalForCard(ev.currentTarget);
    }

    setSendButtonLoading() {
        this.sendBtnEl.disabled = true;
        this.sendBtnEl.innerHTML =
            `<span class="spinner-border spinner-border-sm me-2"` +
            ` role="status" aria-hidden="true"></span>` +
            _t("Sending...");
    }

    resetSendButton() {
        this.sendBtnEl.disabled = false;
        this.sendBtnEl.textContent = this.defaultSendLabel;
    }

    async onSendClick() {
        if (!this.currentMember || this.sendBtnEl.disabled) {
            return;
        }
        this.setSendButtonLoading();
        const shouldFail = this.shouldFailSend;
        try {
            // Placeholder: simulate a network round-trip. No real endpoint
            // is called yet — replace with a `rpc(...)` once the backend
            // contact route is wired up.
            await this.waitFor(
                new Promise((resolve, reject) => {
                    setTimeout(
                        () => (shouldFail ? reject(new Error("simulated")) : resolve()),
                        1000
                    );
                })
            );
            this.bsModal.hide();
            this.services.notification.add(_t("Your message has been sent."), { type: "success" });
        } catch {
            this.resetSendButton();
            this.services.notification.add(_t("Could not send your message."), { type: "danger" });
        }
    }

    onCloseClick() {
        this.bsModal?.hide();
    }

    onModalHidden() {
        this.currentMember = null;
        this.resetSendButton();
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
