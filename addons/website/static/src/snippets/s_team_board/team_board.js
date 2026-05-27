import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

let nextModalId = 0;

const CONTACT_METHODS = "website.team_board.contact_methods";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";
    dynamicContent = {
        ".s_card": {
            "t-on-click": this.onCardClick,
            "t-on-keydown": this.onCardKeydown,
        },
        ".s_team_board_modal_action": {
            "t-on-click": this.onContactMethodClick,
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
        this.actionsEl = this.modalEl.querySelector(".s_team_board_modal_actions");

        this.contactButtons = new Map();
        this.renderContactMethods();

        this.bsModal = window.Modal.getOrCreateInstance(this.modalEl);
        this.registerCleanup(() => this.bsModal.dispose());

        this.currentMember = null;
        this.currentCardEl = null;
    }

    renderContactMethods() {
        if (!this.actionsEl) {
            return;
        }
        this.actionsEl.replaceChildren();
        this.contactButtons.clear();
        const entries = registry.category(CONTACT_METHODS).getEntries();
        entries.sort(([, a], [, b]) => (a.sequence ?? 100) - (b.sequence ?? 100));
        for (const [id, method] of entries) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = `btn ${method.className || "btn-secondary"} s_team_board_modal_action`;
            btn.dataset.methodId = id;
            btn.textContent = method.label;
            this.actionsEl.appendChild(btn);
            this.contactButtons.set(id, { buttonEl: btn, defaultLabel: method.label, method });
        }
    }

    extractMember(cardEl) {
        const titleEl = cardEl.querySelector(".card-title");
        const roleEl = cardEl.querySelector(".card-body .text-muted");
        const bioEl = cardEl.querySelector(".o_team_board_bio");
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

        this.currentMember = member;
        this.currentCardEl = cardEl;
        this.titleEl.textContent = member.name;
        this.roleEl.textContent = member.role;
        this.bioEl.textContent = member.bio;
        this.imgEl.setAttribute("src", member.imgSrc);
        this.imgEl.setAttribute("alt", member.imgAlt || member.name);
        this.resetAllButtons();
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

    setButtonLoading(btn, label) {
        btn.disabled = true;
        btn.textContent = "";

        const spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm me-2";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");

        btn.appendChild(spinner);
        btn.appendChild(document.createTextNode(label || _t("Working...")));
    }

    resetButton(btn, defaultLabel) {
        btn.disabled = false;
        btn.textContent = defaultLabel;
    }

    resetAllButtons() {
        for (const { buttonEl, defaultLabel } of this.contactButtons.values()) {
            this.resetButton(buttonEl, defaultLabel);
        }
    }

    async onContactMethodClick(ev) {
        const btn = ev.currentTarget;
        const id = btn.dataset.methodId;
        const entry = this.contactButtons.get(id);
        if (!entry || !this.currentMember || btn.disabled) {
            return;
        }
        try {
            await entry.method.handler({
                member: this.currentMember,
                cardEl: this.currentCardEl,
                modalEl: this.modalEl,
                services: this.services,
                waitFor: this.waitFor.bind(this),
                closeModal: () => this.bsModal.hide(),
                button: {
                    setLoading: (label) => this.setButtonLoading(btn, label),
                    reset: () => this.resetButton(btn, entry.defaultLabel),
                },
            });
        } catch (err) {
            console.error(`Team board contact method '${id}' threw:`, err);
            this.resetButton(btn, entry.defaultLabel);
        }
    }

    onCloseClick() {
        this.bsModal?.hide();
    }

    onModalHidden() {
        this.currentMember = null;
        this.currentCardEl = null;
        this.resetAllButtons();
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
