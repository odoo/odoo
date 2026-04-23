import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class TeamBoardModal extends Interaction {
    static selector = ".s_team_board_modal";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _envBus: () => this.env.bus,
        _contactButton: () => this.el.querySelector(".s_team_board_contact_button"),
    };
    dynamicContent = {
        _envBus: {
            "t-on-WEBSITE:TEAM_BOARD:MODAL:SHOW": this.onShowModal,
        },
        _root: {
            "t-on-hidden.bs.modal": this.onModalHidden,
        },
        ".s_team_board_modal_name": {
            "t-out": () => this.member.name,
        },
        ".s_team_board_modal_role": {
            "t-out": () => this.member.role,
        },
        ".s_team_board_modal_bio": {
            "t-out": () => this.member.bio,
        },
        ".s_team_board_modal_image": {
            "t-att-src": () => this.member.imageSrc || null,
            "t-att-alt": () => this.member.imageAlt,
        },
        _contactButton: {
            "t-on-click": this.locked(this.onContactButtonClick, true),
            "t-att-disabled": () => this.isSendingContact,
            "t-out": () => (this.isSendingContact ? _t("Sending...") : _t("Send a message")),
        },
    };

    setup() {
        this.isSendingContact = false;
        this.isClosing = false;
        this.member = {};
        this.bsModal = null;
        this.registerCleanup(() => {
            this.bsModal?.dispose();
            this.bsModal = null;
            this.el.remove();
        });
    }

    onShowModal(ev) {
        const state = ev.detail;
        if (!state || state.modalEl !== this.el) {
            return;
        }
        this.member = { ...state.member };
        this.activeMemberEl = state.memberEl || null;
        this.updateContent();
        this.showModal();
    }

    async onContactButtonClick() {
        this.isSendingContact = true;
        this.updateContent();
        try {
            const response = await this.waitFor(
                rpc("/website/team_board/contact", {
                    member_id: this.member.memberId,
                })
            );
            if (!response?.success) {
                throw new Error("contact_failed");
            }
            this.services.notification.add(_t("Your message has been sent."), {
                type: "success",
            });
            this.closeModal();
        } catch {
            this.services.notification.add(_t("Could not send your message."), {
                type: "danger",
            });
        } finally {
            this.isSendingContact = false;
            if (!this.isDestroyed) {
                this.updateContent();
            }
        }
    }

    showModal() {
        this.bsModal = window.Modal.getOrCreateInstance(this.el);
        this.bsModal.show();
    }

    onModalHidden() {
        if (this.isClosing) {
            return;
        }
        this.isClosing = true;
        this.services["public.interactions"].stopInteractions(this.el);
    }

    closeModal() {
        if (this.isClosing) {
            return;
        }
        this.bsModal?.hide();
    }
}

registry.category("public.interactions").add("website.team_board_modal", TeamBoardModal);
